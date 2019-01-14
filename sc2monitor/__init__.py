"""sc2monitor keeps keeps track of large amount StarCraft 2 accounts."""
import asyncio

from sc2monitor.controller import Controller

db_credentials = dict(
    protocol="mysql+pymysql",
    host="localhost",
    user="sc2monitor",
    passwd=None,
    db="sc2monitor")

api_credentials = dict(
    key=None,
    secret=None)


def init(host=None, user=None, passwd=None, db=None, protocol=None,
         api_key=None, api_secret=None):
    """Init the sc2monitor give database and api credentials."""
    if host is not None:
        db_credentials['host'] = host
    if user is not None:
        db_credentials['user'] = user
    if passwd is not None:
        db_credentials['passwd'] = passwd
    if db is not None:
        db_credentials['db'] = db
    if protocol is not None:
        db_credentials['protocol'] = protocol
    if api_key is not None:
        api_credentials['key'] = api_key
    if api_secret is not None:
        api_credentials['secret'] = api_secret


def add_player(url):
    """Add a player to the sc2monitor by Battl.net URL."""
    kwargs = {}
    kwargs['db'] = '{protocol}://{user}:{passwd}@{host}/{db}'.format(
        **db_credentials)
    controller = Controller(**kwargs)
    controller.add_player(url=url)


def remove_player(url):
    """Remove a player off the sc2monitor by Battl.net URL."""
    kwargs = {}
    kwargs['db'] = '{protocol}://{user}:{passwd}@{host}/{db}'.format(
        **db_credentials)
    controller = Controller(**kwargs)
    controller.remove_player(url=url)


async def main_loop():
    """Define the asyncio main loop of the sc2monitor."""
    kwargs = {}

    if db_credentials['passwd'] is not None:
        db = '{protocol}://{user}:{passwd}@{host}/{db}'
    else:
        db = '{protocol}://{user}@{host}/{db}'
    kwargs['db'] = db.format(**db_credentials)

    if api_credentials['key'] is not None:
        kwargs['api_key'] = api_credentials['key']
    if api_credentials['secret'] is not None:
        kwargs['api_secret'] = api_credentials['secret']

    async with Controller(**kwargs) as ctrl:
        await ctrl.run()


def run():
    """Run the sc2monitor."""
    asyncio.run(main_loop())
