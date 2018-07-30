# sc2monitor
Python script that when executed regularly keeps track of large amount StarCraft 2 accounts on the 1vs1 ladder

## Setup
To setup the MySQL tables for you execute the following script once
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
You can add players to monitor either by their sc2_player_id (and realm) or by their Battletag via executing, e.g., `sc2monitor.add_player(player_id=221986, realm=1)` or `sc2monitor.add_player(battle_tag='pressure#2380')`, or by adding a row into player MySQL table with either `sc2_player_id` or `battle_tag` entered.


