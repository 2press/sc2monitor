"""Wrapper for the SC2 api."""
import asyncio
import logging
import re
from datetime import datetime, timedelta

from aiohttp import BasicAuth
from aiohttp.client_exceptions import ClientResponseError, ContentTypeError

import sc2monitor.model as model

logger = logging.getLogger(__name__)


class SC2API:
    """Wrapper for the SC2 api."""

    def __init__(self, controller):
        """Init the sc2 api."""
        self._controller = controller
        try:
            self._session = self._controller.http_session
        except AttributeError:
            self._session = None
        self._key = ''
        self._secret = ''
        self._access_token = ''
        self._access_token_checked = False
        self.read_config()
        try:
            self._access_token_lock = asyncio.Lock()
        except RuntimeError:
            self._access_token_lock = None
        self.request_count = 0
        self.retry_count = 0

        self._precompile()

    def _precompile(self):
        """Precompile regular expression for bnet urls."""
        self._p1 = re.compile(
            r'^https?:\/\/starcraft2.com\/(?:\w+-\w+\/)?'
            r'profile\/([1-5])\/([1-2])\/(\d+)\/?',
            re.IGNORECASE)
        self._p2 = re.compile(
            r'^https?:\/\/(eu|us).battle.net\/sc2\/\w+\/'
            r'(?:\w+\/)*profile\/(\d+)\/([1-2])\/\w+\/?',
            re.IGNORECASE)

    def read_config(self):
        """Read the api key and secret from the config."""
        self._key = self._controller.get_config(
            'api_key', raise_key_error=False)
        self._secret = self._controller.get_config(
            'api_secret', raise_key_error=False)
        new_token = self._controller.get_config(
            'access_token', raise_key_error=False)

        if self._access_token != new_token:
            self._access_token = new_token
            self._access_token_checked = False

    async def check_access_token(self, token):
        """Check if the access token is valid for at least an hour."""
        async with self._session.get(
                'https://eu.battle.net/oauth/check_token',
                params={'token': token}) as resp:
            self.request_count += 1
            valid = resp.status == 200
            if valid:
                json = await resp.json()
                exp = datetime.fromtimestamp(json['exp'])
                valid = valid and exp - datetime.now() >= timedelta(hours=1)
            self._access_token_checked = valid
        return self._access_token_checked

    async def get_access_token(self):
        """Get an valid access token."""
        async with self._access_token_lock:
            if (not self._access_token
                or (not self._access_token_checked
                    and not await self.check_access_token(
                        self._access_token))):
                await self.receive_new_access_token()
            return self._access_token

    async def receive_new_access_token(self):
        """Receive a new acces token vai oauth."""
        data, status = await self._perform_api_request(
            'https://eu.battle.net/oauth/token',
            auth=BasicAuth(
                self._key, self._secret),
            params={'grant_type': 'client_credentials'})

        if status != 200:
            raise InvalidApiResponse(status)

        self._access_token = data.get('access_token')
        self._access_token_checked = True
        self._controller.set_config('access_token', self._access_token)
        logger.info('New access token received.')

    def parse_profile_url(self, url):
        """Parse a profile URL for the server, the realm and the profile ID."""
        m = self._p1.match(url)
        if m:
            server = model.Server(int(m.group(1)))
            realmID = int(m.group(2))
            profileID = int(m.group(3))
        else:
            m = self._p2.match(url)
            if m:
                server = model.Server(2 if m.group(1).lower() == 'eu' else 1)
                profileID = int(m.group(2))
                realmID = int(m.group(3))
            else:
                raise ValueError('Invalid profile url {}'.format(url))
        return server, realmID, profileID

    async def get_season(self, server: model.Server):
        """Collect the current season info."""
        api_url = ('https://eu.api.blizzard.com/sc2/'
                   f'ladder/season/{server.id()}')
        payload = {'locale': 'en_US',
                   'access_token': await self.get_access_token()}
        data, status = await self._perform_api_request(api_url, params=payload)
        if status != 200:
            raise InvalidApiResponse(f'{status}: {api_url}')

        return model.Season(
            season_id=data.get('seasonId'),
            number=data.get('number'),
            year=data.get('year'),
            server=server,
            start=datetime.fromtimestamp(int(data.get('startDate'))),
            end=datetime.fromtimestamp(int(data.get('endDate')))
        )

    async def get_metadata(self, player: model.Player):
        """Collect meta data for a player."""
        return await self._get_metadata(
            player.server, player.realm, player.player_id)

    async def get_ladders(self, player: model.Player):
        """Collect all 1v1 ladders where a player is ranked."""
        return await self._get_ladders(
            player.server, player.realm, player.player_id)

    async def get_ladder_data(self, player: model.Player, ladder_id):
        """Collect data about a player's ladder."""
        async for data in self._get_ladder_data(
                player.server, player.realm, player.player_id, ladder_id):
            yield data

    async def get_match_history(self, player: model.Player):
        """Collect match history of a player."""
        return await self._get_match_history(
            player.server, player.realm, player.player_id)

    async def _get_ladders(self, server: model.Server,
                           realmID, profileID, scope='1v1'):
        """Collect all ladder of a scope where a player is ranked."""
        api_url = ('https://eu.api.blizzard.com/sc2/'
                   f'profile/{server.id()}/{realmID}/{profileID}/'
                   'ladder/summary')
        payload = {'locale': 'en_US',
                   'access_token': await self.get_access_token()}
        data, status = await self._perform_api_request(api_url, params=payload)
        if status != 200:
            raise InvalidApiResponse(f'{status}: {api_url}')
        data = data.get('allLadderMemberships', [])
        ladders = set()
        for ladder in data:
            if ladder.get('localizedGameMode', '').find('1v1') != -1:
                ladder_id = ladder.get('ladderId')
                if ladder_id not in ladders:
                    ladders.add(ladder_id)
        return ladders

    async def _get_metadata(self, server: model.Server,
                            realmID, profileID):
        """Collect a player's meta data."""
        api_url = ('https://eu.api.blizzard.com/sc2/'
                   f'metadata/profile/{server.id()}/{realmID}/{profileID}')
        payload = {'locale': 'en_US',
                   'access_token': await self.get_access_token()}
        data, status = await self._perform_api_request(api_url, params=payload)
        if status != 200:
            raise InvalidApiResponse(f'{status}: {api_url}')
        return data

    async def _get_ladder_data(self, server: model.Server,
                               realmID, profileID, ladderID):
        """Collect data of a specific player's ladder."""
        api_url = ('https://eu.api.blizzard.com/sc2/profile/'
                   f'{server.id()}/{realmID}/{profileID}/ladder/{ladderID}')
        payload = {'locale': 'en_US',
                   'access_token': await self.get_access_token()}
        data, status = await self._perform_api_request(api_url, params=payload)
        if status != 200:
            raise InvalidApiResponse(f'{status}: {api_url}')

        league = model.League.get(data.get('league'))
        found_idx = -1
        found = 0
        used = set()
        for meta_data in data.get('ranksAndPools'):
            mmr = meta_data.get('mmr')

            try:
                idx = meta_data.get('rank') - 1
                team = data.get('ladderTeams')[idx]
                player = team.get('teamMembers')[0]
                used.add(idx)
                if (int(player.get('id')) != profileID
                        or int(player.get('realm')) != realmID):
                    raise InvalidApiResponse(api_url)
            except (IndexError, InvalidApiResponse):
                found = False
                for team_idx in range(
                        found_idx + 1, len(data.get('ladderTeams'))):
                    team = data.get('ladderTeams')[team_idx]
                    player = team.get('teamMembers')[0]
                    if (team_idx not in used):
                        used.add(team_idx)
                        if (int(player.get('id')) == profileID
                                and int(player.get('realm')) == realmID):
                            found_idx = team_idx
                            found = True
                            break

                if not found:
                    raise InvalidApiResponse(api_url)

            if mmr != team.get('mmr'):
                logger.debug(
                    f'{api_url}: MMR in ladder request'
                    f" does not match {mmr} vs {team.get('mmr')}.")
                mmr = team.get('mmr', mmr)
            race = player.get('favoriteRace')
            games = int(team.get('wins')) + int(team.get('losses'))

            yield {
                'mmr': int(mmr),
                'race': model.Race.get(race),
                'games': games,
                'wins': int(team.get('wins')),
                'losses': int(team.get('losses')),
                'name': player.get('displayName'),
                'joined': datetime.fromtimestamp(team.get('joinTimestamp')),
                'ladder_id': int(ladderID),
                'league': league}

    async def _get_match_history(self, server: model.Server,
                                 realmID, profileID, scope='1v1'):
        """Collect matches of a specific scope from the match history."""
        api_url = ('https://eu.api.blizzard.com/sc2/legacy/profile/'
                   f'{server.id()}/{realmID}/{profileID}/matches')
        payload = {'locale': 'en_US',
                   'access_token': await self.get_access_token()}
        data, status = await self._perform_api_request(api_url, params=payload)
        if status != 200:
            raise InvalidApiResponse(f'{status}: {api_url}')

        match_history = []
        for match in data.get('matches', []):
            if match['type'] == scope:
                match_data = {
                    'result': model.Result.get(match['decision']),
                    'datetime': datetime.fromtimestamp(match['date'])}
                match_history.append(match_data)

        return match_history

    async def _perform_api_request(self, url, **kwargs):
        """Perform a generic api request (including retries)."""
        error = ''
        json = {}
        max_retries = 5
        for retries in range(max_retries):
            async with self._session.get(url, **kwargs) as resp:
                self.request_count += 1
                status = resp.status
                if resp.status == 504:
                    error = 'API timeout'
                    self.retry_count += 1
                    continue
                try:
                    resp.raise_for_status()
                except ClientResponseError:
                    error = f'{resp.status}: {resp.reason}'
                    continue
                try:
                    json = await resp.json()
                except ContentTypeError:
                    error = 'Unable to decode JSON'
                    self.retry_count += 1
                    status = 0
                    continue
                json['request_datetime'] = datetime.now()
                break

        if retries == max_retries - 1 and error:
            logger.warning(error)

        return json, status


class InvalidApiResponse(Exception):
    """Invalid API Response exception."""

    def __init__(self, api_url):
        """Init the InvalidApiResponse exception."""
        self.api_url = api_url

    def __str__(self):
        """Return URL of invalid api request."""
        return repr(self.api_url)
