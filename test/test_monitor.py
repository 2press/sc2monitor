"""Test basic function of the sc2monitor."""
import asyncio
import logging
from datetime import datetime, timedelta

import pytest

from sc2monitor import add_player, init, remove_player, run
from sc2monitor.controller import Controller
from sc2monitor.model import Log, Match, Player, Result, Run, Server


async def monitor_loop(**kwargs):
    async with Controller(**kwargs) as ctrl:

        token = await ctrl.sc2api.get_access_token()
        assert token != ''
        assert await ctrl.sc2api.check_access_token(token)

        ctrl.add_player(
            'http://eu.battle.net/sc2/en/profile/221986/1/pressure')
        ctrl.add_player('https://starcraft2.com/en-gb/profile/2/1/1982648')

        await ctrl.run()
        assert ctrl.sc2api.request_count > 0

        run = ctrl.db_session.query(Run).order_by(
            Run.datetime.desc()).limit(1).scalar()

        assert run is not None
        assert run.api_requests == ctrl.sc2api.request_count
        assert run.api_retries == ctrl.sc2api.retry_count
        assert run.duration > 0.0

        errors = ctrl.db_session.query(Log).filter(
            Log.level == 'ERROR').count()
        assert errors == 0

        warnings = ctrl.db_session.query(Log).filter(
            Log.level == 'WARNING').count()
        assert warnings == run.warnings

        player = ctrl.db_session.query(Player).filter(
            Player.player_id == 221986).limit(1).scalar()
        assert player is not None
        assert player.name != ''
        assert player.realm == 1
        assert player.server == Server.Europe
        assert player.player_id == 221986

        player.name = 'Test'
        ctrl.db_session.commit()
        await ctrl.update_player_name(player)
        ctrl.db_session.refresh(player)
        assert player.name != ''

        matches = ctrl.db_session.query(Match).filter(
            Match.player == player).count()
        assert matches <= 25

        player = ctrl.db_session.query(Player).filter(
            Player.player_id == 1982648).order_by(
            Player.wins.desc()).limit(1).scalar()
        assert player is not None
        assert player.name != ''
        assert player.realm == 1
        assert player.server == Server.Europe
        assert player.player_id == 1982648

        player_id = player.id

        player.name = 'Test'
        ctrl.db_session.commit()
        await ctrl.update_player_name(player)
        ctrl.db_session.refresh(player)
        assert player.name != ''
        player.refreshed = datetime.now() - timedelta(days=1)

        matches = ctrl.db_session.query(Match).filter(
            Match.player == player).order_by(
            Match.datetime.desc()).all()
        matches_count = len(matches)
        win_count = player.wins
        loss_count = player.losses
        assert matches_count <= 25
        for position, match in enumerate(matches):
            if match.result == Result.Win:
                player.wins -= 1
            elif match.result == Result.Loss:
                player.losses -= 1
            ctrl.db_session.delete(match)
            player.last_played = match.datetime - timedelta(days=1)

        player.wins = 0
        player.losses = 0
        ctrl.db_session.commit()

        matches = ctrl.db_session.query(Match).filter(
            Match.player == player).count()
        assert matches == 0

        await ctrl.run()

        run = ctrl.db_session.query(Run).order_by(
            Run.datetime.desc()).limit(1).scalar()

        assert run.duration > 0.0

        errors = ctrl.db_session.query(Log).filter(
            Log.level == 'ERROR').count()
        assert errors == 0

        warnings = ctrl.db_session.query(Log).filter(
            Log.level == 'WARNING').count()
        assert warnings == run.warnings

        player = ctrl.db_session.query(Player).filter(
            Player.id == player_id).limit(1).scalar()

        assert player.wins == win_count
        assert player.losses == loss_count

        matches = ctrl.db_session.query(Match).filter(
            Match.player == player).count()

        assert matches == win_count + loss_count

        ctrl.update_ema_mmr(player)

        ctrl.remove_player('https://starcraft2.com/en-gb/profile/2/1/1982648')

        matches = ctrl.db_session.query(Match).filter(
            Match.player_id == player.player_id).count()
        assert matches == 0

        player = ctrl.db_session.query(Player).filter(
            Player.player_id == 1982648).limit(1).scalar()
        assert player is None

        ctrl.remove_player('https://starcraft2.com/en-gb/profile/2/1/221986')

        player = ctrl.db_session.query(Player).filter(
            Player.player_id == 221986).limit(1).scalar()
        assert player is None

        with pytest.raises(ValueError):
            ctrl.get_config('nonexisting_key')

        assert ctrl.get_config(
            'nonexisting_key', raise_key_error=False) == ''

        assert ctrl.get_config(
            'nonexisting_key',
            raise_key_error=False,
            return_object=True) is None

        ctrl.set_config('analyze_matches', 50)
        ctrl.get_config('analyze_matches') == '50'
        ctrl.set_config('analyze_matches', 52)
        cfg_object = ctrl.get_config(
            'analyze_matches',
            return_object=True)
        assert cfg_object is not None
        assert cfg_object.value == str(52)

        with pytest.raises(ValueError):
            ctrl.add_player('pressure#986')

        with pytest.raises(ValueError):
            ctrl.setup(not_valid_key='value')

        ctrl.setup(analyze_matches=50)


def test_monitor(caplog, apikey, apisecret, db, user, passwd, protocol):

    caplog.set_level(logging.ERROR)

    assert apikey != ''
    assert apisecret != ''
    assert protocol != ''

    kwargs = {}

    if protocol == 'sqlite':
        kwargs['db'] = 'sqlite://'
    else:
        assert user != ''
        assert db != ''
        kwargs['db'] = f'{protocol}://{user}:{passwd}@{db}/sc2monitor'

    kwargs['api_key'] = apikey
    kwargs['api_secret'] = apisecret

    asyncio.run(monitor_loop(**kwargs))

    for record in caplog.records:
        assert record.levelname != 'CRITICAL'
        assert record.levelname != 'ERROR'


def test_wrapper(caplog, apikey, apisecret, db, user, passwd, protocol):

    caplog.set_level(logging.ERROR)

    if protocol == 'sqlite':
        return

    init(host=db, user=user, passwd=passwd, protocol=protocol,
         api_key=apikey, api_secret=apisecret, db='sc2monitor')

    add_player('https://starcraft2.com/en-gb/profile/2/1/221986')

    run()

    remove_player('https://starcraft2.com/en-gb/profile/2/1/221986')

    for record in caplog.records:
        assert record.levelname != 'CRITICAL'
        assert record.levelname != 'ERROR'
