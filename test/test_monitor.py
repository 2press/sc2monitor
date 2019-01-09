import asyncio

from sc2monitor.controller import Controller
from sc2monitor.model import Log, Player


async def monitor_loop(**kwargs):
    async with Controller(**kwargs) as ctrl:
        assert await ctrl.sc2api.get_access_token() != ''
        ctrl.add_player('https://starcraft2.com/en-gb/profile/2/1/221986')
        await ctrl.run()
        assert ctrl.sc2api.request_count > 0
        errors = ctrl.db_session.query(Log).filter(
            Log.level != 'INFO').count()
        assert errors == 0
        player = ctrl.db_session.query(Player).filter(
            player.player_id == 221986).limit(1).scalar()
        assert player is not None
        assert player.name != ''


def test_monitor(apikey, apisecret):

    assert apikey != ''
    assert apisecret != ''

    kwargs = {}
    kwargs['db'] = 'mysql+pymysql://travis:@127.0.0.1/sc2monitor'
    kwargs['api_key'] = apikey
    kwargs['api_secret'] = apisecret

    asyncio.run(monitor_loop(**kwargs))
