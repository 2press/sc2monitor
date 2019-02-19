![Python Versions](https://img.shields.io/pypi/pyversions/sc2monitor.svg)
[![PyPi](https://img.shields.io/pypi/v/sc2monitor.svg)](https://pypi.org/project/sc2monitor/)
[![License](https://img.shields.io/github/license/2press/sc2monitor.svg)](https://github.com/2press/sc2monitor/blob/master/LICENSE)
[![Build Status](https://travis-ci.com/2press/sc2monitor.svg?branch=master)](https://travis-ci.com/2press/sc2monitor)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/c201266249ed4901ad2a09f1629e6229)](https://app.codacy.com/app/2press/sc2monitor?utm_source=github.com&utm_medium=referral&utm_content=2press/sc2monitor&utm_campaign=Badge_Grade_Dashboard)
[![codecov](https://codecov.io/gh/2press/sc2monitor/branch/master/graph/badge.svg)](https://codecov.io/gh/2press/sc2monitor)
[![Requirements Status](https://requires.io/github/2press/sc2monitor/requirements.svg?branch=master)](https://requires.io/github/2press/sc2monitor/requirements/?branch=master)

# sc2monitor
Python (>=3.7) script that when executed regularly keeps track of medium amount StarCraft 2 accounts on the 1vs1 ladder

## Installation
Install this Python 3 package via `pip` by executing `pip install sc2monitor`

## Execution
To collect data run the following script regularly (every 5-15 minutes), e.g. via cronjob:
```python
import sc2monitor

sc2monitor.init(host='db-host',
                user='db-user',
                passwd='db-password',
                db='db-database',
                protocol='db-protocol',
                apikey='your-bnet-api-key',
                apisecret='your-bnet-api-secret')
sc2monitor.run()
```
Your API-key `your-bnet-api-key` and secret `your-bnet-api-secret` have to be created by registering an application at <https://develop.battle.net/access/> and have to be passed only once or when you want to change them. If not specified `mysql+pymysql` will be used as database protocol - other protocol options can be found at <https://docs.sqlalchemy.org/en/latest/dialects/>.

If not executed regularly the script will try to make an educated guess for games played since the last execution.

At execution a protocol will be automatically logged to the database.

You can add and remove players to the monitor by passing their StarCraft 2 URL:
```python
# Adding a player
sc2monitor.add_player('https://starcraft2.com/en-gb/profile/2/1/221986')

# Removing a player
sc2monitor.remove_player('https://starcraft2.com/en-gb/profile/2/1/221986')
```

## Data
The collected data (including statistics) can be accessed via the database tables.
