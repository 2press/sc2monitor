import asyncio

from sc2monitor.controller import Controller
from sc2monitor.model import Log, Player, Match, Server


async def monitor_loop(**kwargs):
    async with Controller(**kwargs) as ctrl:
        
        assert await ctrl.sc2api.get_access_token() != ''
        
        ctrl.add_player('https://starcraft2.com/en-gb/profile/2/1/221986')
       
        await ctrl.run()
        assert ctrl.sc2api.request_count > 0

        errors = ctrl.db_session.query(Log).filter(
            Log.level == 'ERROR').count()
        assert errors == 0
        
        player = ctrl.db_session.query(Player).filter(
            Player.player_id == 221986).limit(1).scalar()
        assert player is not None
        assert player.name != ''
        assert player.realm == 1
        assert player.server == Server.Europe
        assert player.player_id == 221986
        
        matches = ctrl.db_session.query(Match).filter(Match.player == player).count()
        assert matches <= 25


def test_monitor(apikey, apisecret, db, user, passwd, protocol):

    assert apikey != ''
    assert apisecret != ''
    assert protocol != ''

    kwargs = {}
    
    if protocol == 'sqlite':
        kwargs['db'] = 'sqlite://'
    else:
        assert user != ''
        assert db != ''
        kwargs['db'] = f'{protocol}//{user}:{passwd}@{db}/sc2monitor'
            
    kwargs['api_key'] = apikey
    kwargs['api_secret'] = apisecret

    asyncio.run(monitor_loop(**kwargs))
