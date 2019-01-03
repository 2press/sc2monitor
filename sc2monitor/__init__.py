import asyncio

from sc2monitor.controller import Controller

db_credentials = dict(
    protocol="mysql+pymysql",
    host="localhost",
    user="sc2monitor",
    passwd="",
    db="sc2monitor")

api_credentials = dict(
    key='',
    secret='')


def init(host='', user='', passwd='', db='', protocol='',
         api_key='', api_secret=''):
    if host:
        db_credentials['host'] = host
    if user:
        db_credentials['user'] = user
    if passwd:
        db_credentials['passwd'] = passwd
    if db:
        db_credentials['db'] = db
    if protocol:
        db_credentials['protocol'] = protocol
    if api_key:
        api_credentials['key'] = api_key
    if api_secret:
        api_credentials['secret'] = api_secret


def add_player(url):
    kwargs = {}
    kwargs['db'] = '{protocol}://{user}:{passwd}@{host}/{db}'.format(
        **db_credentials)
    controller = Controller(**kwargs)
    controller.add_player(url=url)


async def main_loop():
    kwargs = {}
    kwargs['db'] = '{protocol}://{user}:{passwd}@{host}/{db}'.format(
        **db_credentials)
    if api_credentials['key']:
        kwargs['api_key'] = api_credentials['key']
    if api_credentials['secret']:
        kwargs['api_secret'] = api_credentials['secret']

    async with Controller(**kwargs) as ctrl:
        await ctrl.run()


def run():
    asyncio.run(main_loop())
