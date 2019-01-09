import sc2monitor


def test_monitor(apikey, apisecret):
    assert apikey != ''
    assert apisecret != ''

    sc2monitor.init(host='127.0.0.1',
                    user='travis',
                    passwd='',
                    db='sc2monitor',
                    apikey=apikey,
                    apisecret=apisecret)

    sc2monitor.add_player('https://starcraft2.com/en-gb/profile/2/1/221986')

    sc2monitor.run()
