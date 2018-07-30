# sc2monitor
Python script that when executed regularly keeps track of large amount StarCraft 2 accounts on the 1vs1 ladder

## Installation
Install this Python 3 package via `pip` by executing `pip install sc2monitor`

## Setup
To setup the MySQL tables execute the following script once
```python
import sc2monitor

sc2monitor.init(host='mysql-host',
                user='mysql-user',
                passwd='mysql-password',
                db='mysql-database')
sc2monitor.setup(apikey='your-bnet-api-key',
                 apisecret='your-bnet-api-secret')
```
Your API-key `your-bnet-api-key` and secret `your-bnet-api-secret` have to be created by registering an application at https://dev.battle.net/member/register

## Execution
To collect data run the following script regularly (every 5-15 minutes), e.g. via cronjob:
```python
import sc2monitor

sc2monitor.init(host='mysql-host',
                user='mysql-user',
                passwd='mysql-password',
                db='mysql-database')
sc2monitor.run()
```

If not executed reguarly the script will try to make an educated guess for games played since the last execution.

You can add players to monitor either by their SC2 player ID (and realm), for instance for http://eu.battle.net/sc2/en/profile/221986/1/pressure/ the player ID is 221986 and the realm is 1, or by their Battletag via executing, e.g.,
```python
sc2monitor.add_player(player_id=221986, realm=1)
```
```python
sc2monitor.add_player(battle_tag='pressure#2380')
```
or by adding a row into  MySQL table *player* with either `sc2_player_id` or `battle_tag` entered.

## Data
The collected data (including statistics) can be accessed via the MySQL tables.


