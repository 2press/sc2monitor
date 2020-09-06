"""Control the sc2monitor."""
import asyncio
import logging
import math
import time
from datetime import datetime, timedelta
from operator import itemgetter

import aiohttp

import sc2monitor.model as model
from sc2monitor.handlers import SQLAlchemyHandler
from sc2monitor.sc2api import SC2API

logger = logging.getLogger(__name__)
sql_logger = logging.getLogger()


class Controller:
    """Control the sc2monitor."""

    def __init__(self, **kwargs):
        """Init the sc2monitor."""
        self.kwargs = kwargs
        self.sc2api = None
        self.db_session = None
        self.current_season = {}

    async def __aenter__(self):
        """Create a aiohttp and db session that will later be closed."""
        headers = {'Accept-Encoding': 'gzip, deflate'}
        self.http_session = aiohttp.ClientSession(headers=headers)
        self.create_db_session()
        return self

    def create_db_session(self):
        """Create sqlalchemy database session."""
        self.db_session = model.create_db_session(
            db=self.kwargs.pop('db', ''),
            encoding=self.kwargs.pop('encoding', ''))
        self.handler = SQLAlchemyHandler(self.db_session)
        self.handler.setLevel(logging.INFO)
        sql_logger.setLevel(logging.INFO)
        sql_logger.addHandler(self.handler)

        if len(self.kwargs) > 0:
            self.setup(**self.kwargs)
        self.sc2api = SC2API(self)
        self.cache_matches = self.get_config(
            'cache_matches',
            default_value=1000)
        self.analyze_matches = self.get_config(
            'analyze_matches',
            default_value=100)

    async def __aexit__(self, exc_type, exc, tb):
        """Close all aiohtto and database session."""
        await self.http_session.close()
        self.db_session.commit()
        self.db_session.close()
        self.db_session = None

    def get_config(self, key, default_value=None,
                   raise_key_error=True,
                   return_object=False):
        """Read a config value from database."""
        if default_value is not None:
            raise_key_error = False
        entry = self.db_session.query(
            model.Config).filter(model.Config.key == key).scalar()
        if not entry:
            if raise_key_error:
                raise ValueError(f'Unknown config key "{key}"')
            else:
                if return_object:
                    return None
                else:
                    return '' if default_value is None else default_value
        else:
            if return_object:
                return entry
            else:
                return entry.value

    def set_config(self, key, value, commit=True):
        """Save a config value to the database."""
        entry = self.db_session.query(
            model.Config).filter(model.Config.key == key).scalar()
        if not entry:
            self.db_session.add(model.Config(key=key, value=value))
        else:
            entry.value = value
        if commit:
            self.db_session.commit()

    def setup(self, **kwargs):
        """Set up the sc2monitor with api-key and api-secret."""
        valid_keys = ['api_key', 'api_secret',
                      'cache_matches', 'analyze_matches']
        for key, value in kwargs.items():
            if key not in valid_keys:
                raise ValueError(
                    f"Invalid configuration key '{key}'"
                    f" (valid keys: {', '.join(valid_keys)})")
            self.set_config(key, value, commit=False)
        self.db_session.commit()
        if self.sc2api:
            self.sc2api.read_config()

    def add_player(self, url, race=model.Race['Random']):
        """Add a player by url to the sc2monitor."""
        close_db = False
        if self.db_session is None:
            self.create_db_session()
            close_db = True
        server, realm, player_id = self.sc2api.parse_profile_url(url)
        count = self.db_session.query(model.Player).filter(
            model.Player.realm == realm,
            model.Player.player_id == player_id,
            model.Player.server == server).count()
        if count == 0:
            new_player = model.Player(
                realm=realm,
                player_id=player_id,
                server=server,
                race=race)
            self.db_session.add(new_player)
            self.db_session.commit()

        if close_db:
            self.db_session.close()
            self.db_session = None

    def remove_player(self, url):
        """Remove a player by url to the sc2monitor."""
        close_db = False
        if self.db_session is None:
            self.create_db_session()
            close_db = True
        server, realm, player_id = self.sc2api.parse_profile_url(url)

        for player in self.db_session.query(model.Player).filter(
                model.Player.realm == realm,
                model.Player.player_id == player_id,
                model.Player.server == server).all():
            self.db_session.delete(player)

        self.db_session.commit()

        if close_db:
            self.db_session.close()
            self.db_session = None

    async def update_season(self, server: model.Server):
        """Update info about the current season in the database."""
        current_season = await self.sc2api.get_season(server)
        season = self.db_session.query(model.Season).\
            filter(model.Season.server == server).\
            order_by(model.Season.season_id.desc()).\
            limit(1).scalar()

        if not season or current_season.season_id != season.season_id:
            self.db_session.add(current_season)
            self.db_session.commit()
            self.db_session.refresh(current_season)
            logger.info(f'Found a new ladder season: {current_season}')
            return current_season
        else:
            season.start = current_season.start
            season.end = current_season.end
            season.year = current_season.year
            season.number = current_season.number
            self.db_session.commit()
            return season

    async def update_seasons(self):
        """Update seasons info for all servers."""
        servers = [server[0] for server in self.db_session.query(
            model.Player.server).distinct()]

        tasks = []

        for server in servers:
            tasks.append(asyncio.create_task(self.update_season(server)))

        for season in await asyncio.gather(*tasks, return_exceptions=True):
            try:
                if isinstance(season, model.Season):
                    self.current_season[season.server.id()] = season
                else:
                    raise season
            except Exception:
                logger.exception(
                    ('The following exception was'
                     ' raised while updating seasons:'))

    async def query_player(self, player: model.Player):
        """Collect api data of a player."""
        complete_data = []
        for ladder in await self.sc2api.get_ladders(player):
            async for data in self.sc2api.get_ladder_data(player, ladder):
                current_player = await self.get_player_with_race(player, data)
                missing_games, new = self.count_missing_games(
                    current_player, data)
                if missing_games['Total'] > 0:
                    complete_data.append({'player': current_player,
                                          'new_data': data,
                                          'missing': missing_games,
                                          'Win': 0,
                                          'Loss': 0})

        if len(complete_data) > 0:
            await self.process_player(complete_data, new)
        elif (not player.name
                or not isinstance(player.refreshed, datetime)
                or player.refreshed <= datetime.now() - timedelta(days=1)):
            await self.update_player_name(player)

    async def update_player_name(self, player: model.Player, name=''):
        """Update the name of a player from api data."""
        if not name:
            metadata = await self.sc2api.get_metadata(player)
            name = metadata['name']
        for tmp_player in self.db_session.query(model.Player).filter(
                model.Player.player_id == player.player_id,
                model.Player.realm == player.realm,
                model.Player.server == player.server,
                model.Player.name != name).all():
            logger.info(f"{tmp_player.id}: Updating name to '{name}'")
            tmp_player.name = name
        self.db_session.commit()

    async def check_match_history(self, complete_data):
        """Check matches in match history and assign them to races."""
        match_history = await self.sc2api.get_match_history(
            complete_data[0]['player'])

        for match in match_history:
            positive = []
            for data_key, data in enumerate(complete_data):
                needed = data['missing'].get(match['result'].describe(), 0) > 0
                try:
                    datetime_check = (match['datetime']
                                      - data['player'].last_played
                                      > timedelta(seconds=0))
                except TypeError:
                    datetime_check = True
                if (needed and datetime_check):
                    positive.append(data_key)
            if len(positive) == 0:
                continue
            elif len(positive) >= 1:
                # Choose the race with most missing results.
                max_missing = 0
                for key in positive:
                    tmp_missing = complete_data[key][
                        'missing'][match['result'].describe()]
                    if tmp_missing > max_missing:
                        data_key = key
                        max_missing = tmp_missing

                complete_data[data_key][
                    'missing'][match['result'].describe()] -= 1
                complete_data[data_key][match['result'].describe()] += 1
                try:
                    complete_data[data_key]['games'].insert(0, match)
                except KeyError:
                    complete_data[data_key]['games'] = [match]

        try:
            last_played = match['datetime']
        except Exception:
            last_played = datetime.now()

        return last_played, len(match_history)

    async def process_player(self, complete_data, new=False):
        """Process the api data of a player."""
        last_played, len_history \
            = await self.check_match_history(complete_data)

        for race_player in complete_data:
            race_player['missing']['Total'] = race_player['missing']['Win'] + \
                race_player['missing']['Loss']
            if race_player['missing']['Total'] > 0:
                if new:
                    logger.info(
                        f"{race_player['player'].id}: Ignoring "
                        f"{race_player['missing']['Total']} games missing in"
                        f" match history ({len_history}) "
                        "of new player.")
                else:
                    self.guess_games(race_player, last_played)
            self.guess_mmr_changes(race_player)
            await self.update_player(race_player)
            self.calc_statistics(race_player['player'])

    async def update_player(self, complete_data):
        """Update database with new data of a player."""
        player = complete_data['player']
        new_data = complete_data['new_data']
        player.mmr = new_data['mmr']
        player.ladder_id = new_data['ladder_id']
        player.league = new_data['league']
        player.ladder_joined = new_data['joined']
        player.wins = new_data['wins']
        player.losses = new_data['losses']
        player.last_active_season = self.get_season_id(player.server)
        if player.name != new_data['name']:
            await self.update_player_name(
                player,
                new_data['name'])
        if (not player.last_played
                or player.ladder_joined
                > player.last_played):
            player.last_played = player.ladder_joined
        self.db_session.commit()

    def calc_statistics(self, player: model.Player):
        """Recalculate player statistics."""
        self.db_session.refresh(player)
        if not player.statistics:
            stats = model.Statistics(player=player)
            self.db_session.add(stats)
            self.db_session.commit()
            self.db_session.refresh(stats)
        else:
            stats = player.statistics

        matches = self.db_session.query(model.Match).filter(
            model.Match.player_id == player.id).order_by(
            model.Match.datetime.desc()).limit(self.analyze_matches).all()

        stats.games_available = len(matches)
        wma_mmr_denominator = stats.games_available * \
            (stats.games_available + 1.0) / 2.0
        stats.max_mmr = player.mmr
        stats.min_mmr = player.mmr
        stats.current_mmr = player.mmr
        wma_mmr = 0.0
        expected_mmr_value = 0.0
        expected_mmr_value2 = 0.0
        current_wining_streak = 0
        current_losing_streak = 0

        for idx, match in enumerate(matches):
            if match.result == model.Result.Win:
                stats.wins += 1
                current_wining_streak += 1
                current_losing_streak = 0
                if current_wining_streak > stats.longest_wining_streak:
                    stats.longest_wining_streak = current_wining_streak
            elif match.result == model.Result.Loss:
                stats.losses += 1
                current_losing_streak += 1
                current_wining_streak = 0
                if current_losing_streak > stats.longest_losing_streak:
                    stats.longest_losing_streak = current_losing_streak
                if match.max_length <= 120:
                    stats.instant_left_games += 1

            if match.guess:
                stats.guessed_games += 1

            mmr = match.mmr
            wma_mmr += mmr * \
                (stats.games_available - idx) / wma_mmr_denominator
            if stats.max_mmr < mmr:
                stats.max_mmr = mmr
            if stats.min_mmr > mmr:
                stats.min_mmr = mmr
            expected_mmr_value += mmr / stats.games_available
            expected_mmr_value2 += mmr * (mmr / stats.games_available)

        if stats.games_available <= 1:
            stats.lr_mmr_slope = 0.0
            stats.lr_mmr_intercept = expected_mmr_value
        else:
            ybar = expected_mmr_value
            xbar = -0.5 * (stats.games_available - 1)
            numerator = 0
            denominator = 0
            for x, match in enumerate(matches):
                x = -x
                y = match.mmr
                numerator += (x - xbar) * (y - ybar)
                denominator += (x - xbar) * (x - xbar)

            stats.lr_mmr_slope = numerator / denominator
            stats.lr_mmr_intercept = ybar - stats.lr_mmr_slope * xbar

        stats.sd_mmr = round(
            math.sqrt(expected_mmr_value2
                      - expected_mmr_value
                      * expected_mmr_value))
        # critical_idx = min(self.controller.config['no_critical_games'],
        #                   stats.games_available) - 1
        # stats.critical_game_played = matches[critical_idx]["played"]
        stats.avg_mmr = expected_mmr_value
        stats.wma_mmr = wma_mmr

        self.db_session.commit()

    @classmethod
    def guess_games(cls, complete_data, last_played):
        """Guess games of a player if missing in match history."""
        # If a player isn't new in the database and has played more
        # than 25 games since the last refresh or the match
        # history is not available for this player, there are
        # missing games in the match history. These are guessed to be very
        # close to the last game of the match history and in alternating
        # order.
        player = complete_data['player']
        if 'games' not in complete_data:
            complete_data['games'] = []

        logger.info((
            "{}: {} missing games in match "
            + "history - more guessing!").format(
            player.id, complete_data['missing']['Total']))

        try:
            delta = (last_played - player.last_played) / \
                complete_data['missing']['Total']
        except Exception:
            delta = timedelta(minutes=3)

        if delta > timedelta(minutes=3):
            delta = timedelta(minutes=3)

        if delta.total_seconds() <= 0:
            last_played = datetime.now()
            delta = timedelta(minutes=3)

        while (complete_data['missing']['Win'] > 0
               or complete_data['missing']['Loss'] > 0):

            if complete_data['missing']['Win'] > 0:
                last_played = last_played - delta
                complete_data['games'].append(
                    {'datetime': last_played, 'result': model.Result.Win})
                complete_data['missing']['Win'] -= 1
                complete_data['Win'] += 1

            if (complete_data['missing']['Win'] > 0
                    and complete_data['missing']['Win']
                    > complete_data['missing']['Loss']):
                # If there are more wins than losses add
                # a second win before the next loss.
                last_played = last_played - delta
                complete_data['games'].append(
                    {'datetime': last_played, 'result': model.Result.Win})
                complete_data['missing']['Win'] -= 1
                complete_data['Win'] += 1

            if complete_data['missing']['Loss'] > 0:
                last_played = last_played - delta
                complete_data['games'].append(
                    {'datetime': last_played, 'result': model.Result.Loss})
                complete_data['missing']['Loss'] -= 1
                complete_data['Loss'] += 1

            if (complete_data['missing']['Loss'] > 0
                    and complete_data['missing']['Win']
                    < complete_data['missing']['Loss']):
                # If there are more losses than wins add second loss before
                # the next win.
                last_played = last_played - delta
                complete_data['games'].append(
                    {'datetime': last_played, 'result': model.Result.Loss})
                complete_data['missing']['Loss'] -= 1
                complete_data['Loss'] += 1

    def guess_mmr_changes(self, complete_data):
        """Guess MMR change of matches."""
        MMR = complete_data['player'].mmr
        if MMR is None:
            MMR = 0
        totalMMRchange = complete_data['new_data']['mmr'] - MMR
        wins = complete_data['Win']
        losses = complete_data['Loss']
        complete_data['games'] = sorted(
            complete_data.get('games', []), key=itemgetter('datetime'))
        logger.info('{}: Adding {} wins and {} losses!'.format(
            complete_data['player'].id, wins, losses))

        if wins + losses <= 0:
            # No games to guess
            return

        # Estimate MMR change to be +/-21 for a win and losse, each adjusted
        # by the average deviation to achive the most recent MMR value.
        # Is 21 accurate? Yes, as the empirical avrage MMR change is 20.9016
        # according to data gathered by this tool.
        if wins + losses == 1 and MMR != 0:
            MMRchange = abs(totalMMRchange)
        else:
            MMRchange = 21

        if MMR == 0:
            totalMMRchange = MMRchange * (wins - losses)
            MMR = complete_data['new_data']['mmr'] - totalMMRchange

        while True:
            avgMMRadjustment = (totalMMRchange - MMRchange
                                * (wins - losses)) / (wins + losses)

            # Make sure that sign of MMR change is correct
            if abs(avgMMRadjustment) >= MMRchange and MMRchange <= 50:
                MMRchange += 1
                logger.info(f"{complete_data['player'].id}:"
                            f" Adjusting avg. MMR change to {MMRchange}")
            else:
                break

        last_played = complete_data['player'].last_played

        previous_match = self.db_session.query(model.Match).\
            filter(model.Match.player_id
                   == complete_data['player'].id).\
            order_by(model.Match.datetime.desc()).limit(1).scalar()

        # Warning breaks Travis CI
        # if not previous_match:
        #     logger.warning('{}: No previous match found.'.format(
        #         complete_data['player'].id))

        for idx, match in enumerate(complete_data['games']):
            estMMRchange = round(
                MMRchange * match['result'].change() + avgMMRadjustment)
            MMR = MMR + estMMRchange
            try:
                delta = match['datetime'] - last_played
            except Exception:
                delta = timedelta(minutes=3)
            last_played = match['datetime']
            max_length = delta.total_seconds()
            # Don't mark the most recent game as guess, as time and mmr value
            # should be accurate (but not mmr change).
            guess = not (idx + 1 == len(complete_data['games']))
            alpha = 2.0 / (100.0 + 1.0)
            if previous_match and previous_match.ema_mmr > 0.0:
                delta = MMR - previous_match.ema_mmr
                ema_mmr = previous_match.ema_mmr + alpha * delta
                emvar_mmr = (1.0 - alpha) * \
                    (previous_match.emvar_mmr + alpha * delta * delta)
            else:
                ema_mmr = MMR
                emvar_mmr = 0.0

            new_match = model.Match(
                player=complete_data['player'],
                result=match['result'],
                datetime=match['datetime'],
                mmr=MMR,
                mmr_change=estMMRchange,
                guess=guess,
                ema_mmr=ema_mmr,
                emvar_mmr=emvar_mmr,
                max_length=max_length)
            complete_data['player'].last_played = match['datetime']
            self.db_session.add(new_match)
            previous_match = new_match

        self.db_session.commit()

        # Delete old matches:
        deletions = 0
        for match in self.db_session.query(model.Match).\
                filter(model.Match.player_id == complete_data['player'].id).\
                order_by(model.Match.datetime.desc()).\
                offset(self.cache_matches).all():
            self.db_session.delete(match)
            deletions += 1
        if deletions > 0:
            self.db_session.commit()
            logger.info(f"{complete_data['player'].id}: "
                        f"{deletions} matches deleted!")

    def update_ema_mmr(self, player: model.Player):
        """Update the exponential moving avarage MMR of a player."""
        matches = self.db_session.query(model.Match).\
            filter(model.Match.player == player).\
            order_by(model.Match.datetime.asc()).all()

        previous_match = None
        for match in matches:
            alpha = 2.0 / (100.0 + 1.0)
            if previous_match and previous_match.ema_mmr > 0.0:
                delta = match.mmr - previous_match.ema_mmr
                ema_mmr = previous_match.ema_mmr + alpha * delta
                emvar_mmr = (1.0 - alpha) * \
                    (previous_match.emvar_mmr + alpha * delta * delta)
            else:
                ema_mmr = match.mmr
                emvar_mmr = 0.0

            match.ema_mmr = ema_mmr
            match.emvar_mmr = emvar_mmr
            previous_match = match
        self.db_session.commit()

    def get_season_id(self, server: model.Server):
        """Get the current season id on a server."""
        return self.current_season[server.id()].season_id

    def count_missing_games(self, player: model.Player, data):
        """Count games of the api data that are not yet in the database."""
        missing = {}
        missing['Win'] = data['wins']
        missing['Loss'] = data['losses']
        if player.last_active_season == 0 or player.mmr == 0:
            new = True
        elif (player.last_active_season < self.get_season_id(player.server)):
            # New Season!
            # TODO: Check if last season endpoint can be requested!
            # Only the legacy endpoints give the option to query the
            # previous season's data (given that the ladder ID is
            # known), e.g.:
            # https://eu.api.blizzard.com/sc2/legacy/ladder/2/209966
            new = False
        elif (player.ladder_id != data['ladder_id']
                or not player.ladder_joined
                or player.ladder_joined < data['joined']
                or data['wins'] < player.wins
                or data['losses'] < player.losses):
            # Old season, but new ladder or same ladder, but rejoined
            if (data['wins'] < player.wins
                    or data['losses'] < player.losses):
                # Forced ladder reset!
                logger.info('{}: Manual ladder reset to {}!'.format(
                    player.id, data['ladder_id']))
                new = True
            else:
                # Promotion?!
                missing['Win'] -= player.wins
                missing['Loss'] -= player.losses
                new = player.mmr == 0
                if missing['Win'] + missing['Loss'] == 0:
                    # Player was promoted/demoted to/from GM!
                    promotion = data['league'] == model.League.Grandmaster
                    demotion = player.league == model.League.Grandmaster
                    if promotion == demotion:
                        logger.warning(
                            'Logical error in GM promotion/'
                            'demotion detection.')
                    player.ladder_joined = data['joined']
                    player.ladder_id = data['ladder_id']
                    player.league = data['league']
                    self.db_session.commit()
                    logger.info(f"{player.id}: GM promotion/demotion.")
                else:
                    if data['league'] < player.league:
                        logger.warning('Logical error in promtion detection.')
                    else:
                        logger.info(f"{player.id}: Promotion "
                                    f"to ladder {data['ladder_id']}!")
        else:
            missing['Win'] -= player.wins
            missing['Loss'] -= player.losses
            new = player.mmr == 0

        missing['Total'] = missing['Win'] + missing['Loss']

        if (missing['Total']) > 0:
            logger.info(
                '{player}: {Total} new matches found!'.format(
                    player=player.id, **missing))

        return missing, new

    async def get_player_with_race(self, player, ladder_data):
        """Get the player with the race present in the ladder data."""
        if player.ladder_id == 0:
            player.race = ladder_data['race']
            correct_player = player
        elif player.race != ladder_data['race']:
            correct_player = self.db_session.query(model.Player).filter(
                model.Player.player_id == player.player_id,
                model.Player.realm == player.realm,
                model.Player.server == player.server,
                model.Player.race == ladder_data['race']).scalar()
            if not correct_player:
                correct_player = model.Player(
                    player_id=player.player_id,
                    realm=player.realm,
                    server=player.server,
                    race=ladder_data['race'],
                    ladder_id=0)
                self.db_session.add(correct_player)
                self.db_session.commit()
                self.db_session.refresh(correct_player)
        else:
            correct_player = player

        return correct_player

    async def run(self):
        """Run the sc2monitor."""
        start_time = time.time()
        logger.debug("Starting job...")

        await self.update_seasons()

        unique_group = (model.Player.player_id,
                        model.Player.realm, model.Player.server)
        tasks = []
        players = self.db_session.query(model.Player).distinct(
            *unique_group).group_by(*unique_group).all()

        for player in players:
            tasks.append(asyncio.create_task(self.query_player(player)))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for key, result in enumerate(results):
            try:
                if result is not None:
                    raise result
            except Exception:
                logger.exception(
                    'The following exception was'
                    f' raised while quering player {players[key].id}:')

        if False:
            for player in self.db_session.query(
                    model.Player).all():
                self.update_ema_mmr(player)

        duration = time.time() - start_time
        self.db_session.add(
            model.Run(duration=duration,
                      api_requests=self.sc2api.request_count,
                      api_retries=self.sc2api.retry_count,
                      warnings=self.handler.warnings,
                      errors=self.handler.errors))
        self.db_session.commit()

        logger.debug(f"Finished job performing {self.sc2api.request_count}"
                     f" api requests ({self.sc2api.retry_count} retries)"
                     f" in {duration:.2f} seconds.")
