import logging
import math
import os
import sys
import threading
import time
import urllib.parse
from datetime import datetime, timedelta
from itertools import product
from operator import itemgetter
from queue import Empty, Queue

import pymysql.cursors
import requests
from requests.auth import HTTPBasicAuth

mysql_credentials = dict(
    host="localhost",
    user="sc2monitor",
    passwd="",
    db="sc2monitor")

mysql_tables = dict(
    config='sc2monitor-config',
    player='sc2monitor-player',
    matchhistory='sc2monitor-matchhistory',
    metadata='sc2monitor-metadata')

basedir = os.path.dirname(sys.modules['__main__'].__file__)
logfile = os.path.join(basedir, 'sc2monitor.log')

# create logger with 'sc2monitor'
logger = logging.getLogger('sc2monitor')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler(logfile)
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter(
    '%(asctime)s, %(name)s, %(levelname)s: %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S")
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)


table_structure = dict()

table_structure['config'] = """CREATE TABLE IF NOT EXISTS `{}` (
`ID` int(10) unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
`name` varchar(32) NOT NULL UNIQUE KEY,
`value` varchar(32) NOT NULL
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8
COLLATE=utf8_general_ci;
"""

table_structure['player'] = """CREATE TABLE IF NOT EXISTS `{}` (
`ID` int(10) unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `sc2_player_id` int(10) unsigned NOT NULL,
  `realm` tinyint(1) NOT NULL DEFAULT '1',
  `sc2_name` varchar(64) NOT NULL DEFAULT '',
  `battle_tag` varchar(64) NOT NULL DEFAULT '',
  `mmr` smallint(5) unsigned NOT NULL DEFAULT '0',
  `ladder_id` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `league` tinyint(1) NOT NULL DEFAULT '0',
  `league_tier` tinyint(1) unsigned NOT NULL DEFAULT '3',
  `race` varchar(64) NOT NULL DEFAULT '',
  `wins` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `losses` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `ties` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `last_played` datetime DEFAULT NULL,
  `last_active_season` tinyint(3) NOT NULL DEFAULT '0',
  `refreshed` datetime DEFAULT NULL
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8
COLLATE=utf8_general_ci;"""

table_structure['matchhistory'] = """CREATE TABLE IF NOT EXISTS `{}` (
`ID` int(10) unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `playerID` int(10) unsigned NOT NULL,
  `result` tinyint(1) NOT NULL DEFAULT '0',
  `played` datetime DEFAULT NULL,
  `mmr` smallint(5) unsigned NOT NULL DEFAULT '0',
  `mmr_change` smallint(4) NOT NULL DEFAULT '0',
  `guess` tinyint(1) NOT NULL DEFAULT '1',
  `max_length` smallint(5) unsigned NOT NULL DEFAULT '0'
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8
COLLATE=utf8_general_ci;"""

table_structure['metadata'] = """CREATE TABLE IF NOT EXISTS `{}` (
`ID` int(10) unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `playerID` int(10) unsigned NOT NULL,
  `games_available` tinyint(3) unsigned NOT NULL DEFAULT '0',
  `wins` tinyint(3) NOT NULL DEFAULT '0',
  `losses` tinyint(3) NOT NULL DEFAULT '0',
  `ties` tinyint(3) NOT NULL DEFAULT '0',
  `critical_game_played` datetime DEFAULT NULL,
  `winrate` float NOT NULL DEFAULT '0',
  `current_mmr` smallint(5) NOT NULL DEFAULT '0',
  `avg_mmr` smallint(5) NOT NULL DEFAULT '0',
  `wma_mmr` smallint(5) unsigned NOT NULL DEFAULT '0',
  `sd_mmr` smallint(5) unsigned NOT NULL DEFAULT '0',
  `max_mmr` smallint(5) unsigned NOT NULL DEFAULT '0',
  `min_mmr` smallint(5) unsigned NOT NULL DEFAULT '0',
  `lr_mmr_slope` float NOT NULL DEFAULT '0',
  `lr_mmr_intercept` float NOT NULL DEFAULT '0',
  `longest_wining_streak` tinyint(3) unsigned NOT NULL DEFAULT '0',
  `longest_losing_streak` tinyint(3) NOT NULL DEFAULT '0',
  `instant_left_games` tinyint(3) NOT NULL DEFAULT '0',
  `guessed_games` tinyint(3) NOT NULL
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8
COLLATE=utf8_general_ci;"""


def init(host='', user='', passwd='', db=''):
    if host:
        mysql_credentials['host'] = host
    if user:
        mysql_credentials['user'] = user
    if passwd:
        mysql_credentials['passwd'] = passwd
    if db:
        mysql_credentials['db'] = db


def setup(apikey, apisecret, no_games=250, no_critical_games=50,
          no_league_worker=7, no_ladder_worker=16, no_player_worker=4,
          no_meta_worker=4):
    connection = pymysql.connect(
        host=mysql_credentials['host'], user=mysql_credentials['user'],
        password=mysql_credentials['passwd'], db=mysql_credentials['db'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cursor:
            for key, structure in table_structure.items():
                sql = structure.format(mysql_tables[key])
                cursor.execute(sql)
            connection.commit()

            sql = "REPLACE INTO `{}` (`name`, `value`) VALUES (%s, %s)"
            sql = sql.format(mysql_tables['config'])
            cursor.execute(sql, ('apikey', apikey))
            cursor.execute(sql, ('apisecret', apisecret))
            cursor.execute(sql, ('no_games', no_games))
            cursor.execute(sql, ('no_critical_games', no_critical_games))
            cursor.execute(sql, ('current_season', 35))
            cursor.execute(sql, ('access_token', ''))
            cursor.execute(sql, ('no_league_worker', no_league_worker))
            cursor.execute(sql, ('no_ladder_worker', no_ladder_worker))
            cursor.execute(sql, ('no_player_worker', no_player_worker))
            cursor.execute(sql, ('no_meta_worker', no_meta_worker))
            connection.commit()
    finally:
        connection.close()


def add_player(player_id=None, realm=1, battle_tag=None):
    connection = pymysql.connect(
        host=mysql_credentials['host'], user=mysql_credentials['user'],
        password=mysql_credentials['passwd'], db=mysql_credentials['db'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor)
    try:
        if player_id is not None:
            sql = "INSERT INTO `{}` (`sc2_player_id`, `realm`) VALUES (%s, %s)"
            with connection.cursor() as cursor:
                sql = sql.format(mysql_tables['player'])
                cursor.execute(sql, (player_id, realm))
            connection.commit()
        elif battle_tag is not None:
            with connection.cursor() as cursor:
                sql = "INSERT INTO `{}` (`battle_tag`) VALUES (%s)"
                sql = sql.format(mysql_tables['player'])
                cursor.execute(sql, (battle_tag))
            connection.commit()
        else:
            raise ValueError(
                'Enter either player_id (and realm) or battle_tag.')
    finally:
        connection.close()


def run():
    """Update and process data."""
    start_time = time.time()
    logger.info("Starting job!")
    try:
        db = pymysql.connect(
            host=mysql_credentials['host'], user=mysql_credentials['user'],
            password=mysql_credentials['passwd'], db=mysql_credentials['db'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor)
    except Exception as e:
        logger.exception("message")
    else:
        try:
            controller = WorkFlowController(db)
            controller.doJob()
        finally:
            db.close()

    try:
        requestCounter = controller.requestCounter
        retryCounter = controller.retryCounter
    except UnboundLocalError:
        requestCounter = 0
        retryCounter = 0

    logger.info(("Finished job performing {} api requests" +
                 " ({} retries) in {:.2f} seconds.").format(
        requestCounter, retryCounter,
        time.time() - start_time))


def compose_mysql_update_cmd(table, update_dic, where_dic, skip_keys=[]):
    """Compose a mysql update cmd from dictionaries."""

    if table in mysql_tables:
        table = mysql_tables[table]

    update_keys = []
    update_values = []

    for key, value in update_dic.items():
        if key in skip_keys:
            continue
        update_keys.append(key + "=%s")
        update_values.append(value)

    where_keys = []
    where_values = []

    for key, value in where_dic.items():
        where_keys.append(key + "=%s")
        where_values.append(value)

    query = "UPDATE `{}` SET ".format(table)
    query = query + ", ".join(update_keys)
    query = query + " WHERE " + " AND ".join(where_keys)
    data = tuple(update_values + where_values)

    return query, data


def compose_mysql_insert_cmd(table, insert_dic, skip_keys=[]):
    """Compose a mysql insert cmd from dictionaries."""

    if table in mysql_tables:
        table = mysql_tables[table]

    insert_keys = []
    insert_values = []

    for key, value in insert_dic.items():
        if key in skip_keys:
            continue
        insert_keys.append(key)
        insert_values.append(value)
    query = 'INSERT INTO `{}`'.format(table)
    query = query + ' ('
    query = query + ", ".join(insert_keys)
    query = query + ") VALUES ("
    query = query + ", ".join(len(insert_keys) * ["%s"]) + ")"
    data = tuple(insert_values)

    return query, data


class WorkFlowController:
    """Control the work flow."""

    semaphoreApiRequest = threading.Semaphore(16)
    dbLock = threading.RLock()
    cLock = threading.RLock()
    sc2ApiParams = {'local': 'en_GB'}
    dataApiParams = {}
    currentSeason = 35
    config = {}

    def __init__(self, db):
        """Init the controller."""
        self.leagueQueue = Queue()
        self.ladderQueue = Queue()
        self.playerQueue = Queue()
        self.metaQueue = Queue()
        self.playerIDs = set()
        self.requestCounter = 0
        self.retryCounter = 0
        self.db = db
        self.worker = []

        # Load Config from MySQL db
        self.loadConfig()

        self.dataApiParams['access_token'] = self.config['access_token']
        self.sc2ApiParams['apikey'] = self.config['apikey']

    def performApiRequest(self, url):
        """Perfom an api request."""
        while True:
            with self.semaphoreApiRequest:
                r = requests.get(url)
            with self.cLock:
                self.requestCounter += 1

            # Retry in case of a timeout
            if r.status_code != 504:
                break
            else:
                logger.info("API timeout")
                with self.cLock:
                    self.retryCounter += 1

        jsonData = r.json()
        jsonData['request_datetime'] = datetime.now()

        return jsonData, r.status_code

    def checkAccessToken(self):
        """Check if bnet api access token is valid."""
        url = "https://eu.battle.net/oauth/check_token?token={}"
        _, status = self.performApiRequest(
            url.format(self.config['access_token']))

        if status != 200:
            self.getAccessToken()

    def getAccessToken(self):
        """Get a new bnet api access token."""
        response = requests.request(
            'POST',
            'https://eu.battle.net/oauth/token',
            auth=HTTPBasicAuth(self.config['apikey'],
                               self.config['apisecret']),
            params=dict(
                grant_type='client_credentials'),
            allow_redirects=False)

        response.raise_for_status()

        data = response.json()
        self.config['access_token'] = data['access_token']
        self.dataApiParams['access_token'] = data['access_token']

        query, data = compose_mysql_update_cmd('config',
                                               {'value': data['access_token']},
                                               {'name': 'access_token'})

        with self.dbLock:
            with self.db.cursor() as cursor:
                cursor.execute(query, data)
            self.db.commit()

        logger.info("Retrieved new access_token")

    def getCurrentSeason(self):
        """Get the id of the current season."""
        params = urllib.parse.urlencode(self.dataApiParams)
        url = "https://eu.api.battle.net/data/sc2/season/current?{}".format(
            params)
        jsonData, status = self.performApiRequest(url)
        if status != 200:
            raise Exception('Request Error {}'.format(status))

        self.currentSeason = jsonData['id']

        query, data = compose_mysql_update_cmd('config',
                                               {'value': self.currentSeason},
                                               {'name': 'current_season'})

        with self.dbLock:
            with self.db.cursor() as cursor:
                cursor.execute(query, data)
            self.db.commit()

    def startThreads(self):
        """Start various parallel threads that do the work."""
        for leagueID in range(self.config.get('no_league_worker', 7)):
            self.worker.append(LeagueDataWorker(self))

        for i in range(self.config.get('no_ladder_worker', 16)):
            self.worker.append(LadderDataWorker(self))

        for i in range(self.config.get('no_player_worker', 4)):
            self.worker.append(PlayerDataWorker(self))

        for i in range(self.config.get('no_meta_worker', 4)):
            self.worker.append(MetaDataWorker(self))

    def doJob(self):
        """Start the work."""
        self.checkAccessToken()
        self.getPlayerIDs()
        self.getCurrentSeason()
        if len(self.playerIDs) > 0:
            self.startThreads()

            try:
                # Search all leagues from bronze (0) to grandmaster (6)
                for leagueID in range(7):
                    self.leagueQueue.put(
                        {'season_id': self.currentSeason,
                         'league_id': leagueID})

                # Wait for workers to finish their work
                self.leagueQueue.join()
                self.ladderQueue.join()
                self.playerQueue.join()
                self.metaQueue.join()
            finally:
                self.stopThreads()

    def getPlayerIDs(self):
        """Get relevant player ids."""

        with self.dbLock:
            query = "SELECT sc2_player_id, battle_tag  FROM `{}`"
            with self.db.cursor() as cursor:
                cursor.execute(query.format(mysql_tables['player']))
                data = cursor.fetchall()
        for row in data:
            if row['sc2_player_id'] == 0:
                id = row['battle_tag']
            else:
                id = row['sc2_player_id']
            self.playerIDs.add(id)

    def stopThreads(self):
        """Stop all threads."""
        for thread in self.worker:
            thread.stop()

    def loadConfig(self):
        """Load config form mysql db."""
        with self.dbLock:
            with self.db.cursor() as cursor:
                query = "SELECT name, value FROM `{}`"
                cursor.execute(query.format(mysql_tables['config']))
                data = cursor.fetchall()

        for item in data:
            try:
                value = int(item['value'])
            except ValueError:
                value = item['value']

            self.config[item['name']] = value


class LeagueDataWorker(threading.Thread):
    """Worker to get all the ladder ids."""

    def __init__(self, controller):
        """Init worker."""
        super().__init__()
        self.setDaemon(True)
        self.controller = controller
        self._stop_event = threading.Event()
        self.start()

    def stop(self):
        """Stop thread."""
        self._stop_event.set()

    def stopped(self):
        """Check if thread was stopped."""
        return self._stop_event.is_set()

    def run(self):
        """Run the task."""
        while not self.stopped():
            try:
                item = self.controller.leagueQueue.get(timeout=3)
            except Empty:
                continue
            try:
                self.doWork(item)
            except Exception as e:
                logger.exception("message")
            finally:
                self.controller.leagueQueue.task_done()

    def doWork(self, data):
        """Process data."""
        leagueID = data['league_id']
        seasonID = data['season_id']
        params = urllib.parse.urlencode(self.controller.dataApiParams)
        url = "https://eu.api.battle.net/data/sc2/league/{}/201/0/{}?{}"
        url = url.format(seasonID, leagueID, params)
        jsonData, status = self.controller.performApiRequest(url)
        if status != 200:
            raise Exception('Request Error {}'.format(status))
        for tier in jsonData['tier']:
            tierID = tier['id'] + 1
            try:
                for division in tier['division']:
                    ladder = {}
                    ladder['league_id'] = leagueID
                    ladder['tier_id'] = tierID
                    ladder['ladder_id'] = division['ladder_id']
                    ladder['season_id'] = seasonID
                    self.controller.ladderQueue.put(ladder)
            except KeyError:
                continue


class LadderDataWorker(threading.Thread):
    """Work to process all ladders and search for players."""

    def __init__(self, controller):
        """Init worker."""
        super().__init__()
        self.setDaemon(True)
        self.controller = controller
        self._stop_event = threading.Event()
        self.start()

    def stop(self):
        """Stop thread."""
        self._stop_event.set()

    def stopped(self):
        """Check if thread was stopped."""
        return self._stop_event.is_set()

    def run(self):
        """Run the task."""
        while not self.stopped():
            try:
                item = self.controller.ladderQueue.get(timeout=3)
            except Empty:
                continue
            try:
                self.doWork(item)
            except Exception as e:
                logger.exception("message")
            finally:
                self.controller.ladderQueue.task_done()

    def doWork(self, inputData):
        """Process the data."""
        params = urllib.parse.urlencode(self.controller.dataApiParams)
        url = 'https://eu.api.battle.net/data/sc2/ladder/{}?{}'.format(
            inputData['ladder_id'], params)
        jsonData, status = self.controller.performApiRequest(url)
        if status != 200:
            raise Exception('Request Error {}'.format(status))

        for player in jsonData['team']:
            # For some reason and since ~ April 2018, there are corrupt
            # datasets - skip these.
            try:
                player_id = player['member'][0]['legacy_link']['id']
                bnet_tag = player['member'][0]['character_link']['battle_tag']
            except KeyError:
                continue

            if (player_id in self.controller.playerIDs or
                    bnet_tag in self.controller.playerIDs):
                data = {}
                data['sc2_player_id'] = player_id
                data['sc2_name'] = player['member'][0]['legacy_link']['name']
                data['realm'] = player['member'][0]['legacy_link']['realm']
                data['battle_tag'] = bnet_tag
                data['mmr'] = player['rating']
                data['league'] = inputData['league_id']
                data['ladder_id'] = inputData['ladder_id']
                data['last_active_season'] = inputData['season_id']
                data['league_tier'] = inputData['tier_id']
                data['race'] = (player['member'][0]
                                ['played_race_count'][0]
                                ['race']['en_US'])
                data['wins'] = player['wins']
                data['losses'] = player['losses']
                data['ties'] = player['ties']
                data['current_win_streak'] = player['current_win_streak']
                # data['join_time_stamp'] = player['join_time_stamp']
                data['last_played'] = datetime.fromtimestamp(
                    player['last_played_time_stamp'])
                data['refreshed'] = jsonData['request_datetime']
                self.controller.playerQueue.put(data)


class PlayerDataWorker(threading.Thread):
    """Worker to process data of a player."""

    def __init__(self, controller):
        """Init worker."""
        super().__init__()
        self.setDaemon(True)
        self.controller = controller
        self._stop_event = threading.Event()
        self.start()

    def stop(self):
        """Stop thread."""
        self._stop_event.set()

    def stopped(self):
        """Check if thread was stopped."""
        return self._stop_event.is_set()

    def run(self):
        """Run the task."""
        while not self.stopped():
            try:
                item = self.controller.playerQueue.get(timeout=3)
            except Empty:
                continue
            try:
                self.doWork(item)
            except Exception as e:
                logger.exception("message")
            finally:
                self.controller.playerQueue.task_done()

    def doWork(self, inputData):
        """Process the data."""
        self.controller.dbLock.acquire()
        query = "SELECT * FROM `{}` WHERE " +\
            "(sc2_player_id='{}' OR battle_tag='{}') " +\
            "AND (race = '{}' OR race = '') LIMIT 1"
        with self.controller.db.cursor() as cursor:
            cursor.execute(query.format(
                mysql_tables['player'],
                inputData['sc2_player_id'],
                inputData['battle_tag'],
                inputData['race']))
            if cursor.rowcount > 0:
                data = cursor.fetchone()
                self.controller.dbLock.release()
                self.processData(data, inputData)
                self.updateData(inputData, data['race'])
            else:
                self.controller.dbLock.release()
                self.insertData(inputData)

    def updateData(self, inputData, race=''):
        """Update data in mysql player table."""
        inputData["last_played"] = inputData["last_played"].strftime(
            '%Y-%m-%d %H:%M:%S')
        inputData["refreshed"] = inputData["refreshed"].strftime(
            '%Y-%m-%d %H:%M:%S')

        where = dict(race=race)
        skip = ["current_win_streak"]

        query, data = compose_mysql_update_cmd(
            'player', inputData, where, skip)

        query += " AND (sc2_player_id=%s OR battle_tag=%s)"
        data += (inputData['sc2_player_id'], inputData['battle_tag'])

        with self.controller.dbLock:
            with self.controller.db.cursor() as cursor:
                cursor.execute(query, data)
            self.controller.db.commit()

    def insertData(self, inputData):
        """Insert data to mysql player table."""
        inputData["last_played"] = inputData["last_played"].strftime(
            '%Y-%m-%d %H:%M:%S')
        inputData["refreshed"] = inputData["refreshed"].strftime(
            '%Y-%m-%d %H:%M:%S')

        skip = ["current_win_streak"]

        query, data = compose_mysql_insert_cmd('player', inputData, skip)

        with self.controller.dbLock:
            with self.controller.db.cursor() as cursor:
                cursor.execute(query, data)
            self.controller.db.commit()

    def processData(self, oldData, newData):
        """Process data."""
        if oldData['last_active_season'] < newData['last_active_season']:
            # Player is for the first time active in the current season
            logger.info(
                "{} active for the first time this season.".format(
                    oldData['ID']))
            if (oldData['last_active_season'] + 1 ==
                    newData['last_active_season']):
                # Think about processing season endpoint of
                # last season and look for new games here.
                # But if the script is executed regularly such
                # matches should not occure.
                # However, they occure if the api data is not updating
                # as it was currently happening in January 2018:
                # Added, but never checked if it is working
                lastSeasonData = self.getLastSeasonData(oldData)
                misWins = max(lastSeasonData['wins'] - oldData['wins'], 0)
                misLosses = max(
                    lastSeasonData['losses'] - oldData['losses'], 0)
                misTies = max(lastSeasonData['ties'] - oldData['ties'], 0)
                newData['wins'] += misWins
                newData['losses'] += misLosses
                newData['ties'] += misTies
                if(misWins > 0 or misLosses > 0 or misTies > 0):
                    logger.info(("{}: Found additional matches in the "
                                 "data of last season ({} wins,"
                                 " {} losses, {} ties)!").format(
                        oldData['ID'], misWins, misLosses, misTies))
            oldData['wins'] = 0
            oldData['losses'] = 0
            oldData['ties'] = 0
            self.processGames(oldData, newData)
        elif(oldData['wins'] == newData['wins'] and
             oldData['losses'] == newData['losses'] and
             oldData['ties'] == newData['ties']):
            # Old Seasons, no change: Nothing to do
            pass
        elif(oldData['wins'] > newData['wins'] or
             oldData['losses'] > newData['losses'] or
                oldData['ties'] > newData['ties']):
            # Old Season, but stats were reset
            oldData['wins'] = 0
            oldData['losses'] = 0
            oldData['ties'] = 0
            self.processGames(oldData, newData)
        else:
            # Old Seasons, but new games:
            self.processGames(oldData, newData)

    def getLastSeasonData(self, oldData):
        """Process last season's endpoint and check for missing games."""
        params = urllib.parse.urlencode(self.controller.dataApiParams)
        url = 'https://eu.api.battle.net/data/sc2/ladder/{}?{}'.format(
            oldData['ladder_id'], params)
        jsonData, status = self.controller.performApiRequest(url)
        if status != 200:
            raise Exception('Request Error {}'.format(status))

        for player in jsonData['team']:
            # For some reason and since ~ April 2018, there are corrupt
            #  datasets - skip these.
            try:
                player_id = player['member'][0]['legacy_link']['id']
            except KeyError:
                continue
            if player_id == oldData['sc2_player_id']:
                data = {}
                data['sc2_player_id'] = player_id
                data['sc2_name'] = player['member'][0]['legacy_link']['name']
                data['realm'] = player['member'][0]['legacy_link']['realm']
                data['battle_tag'] = (player['member'][0]
                                      ['character_link']['battle_tag'])
                data['mmr'] = player['rating']
                data['league'] = oldData['league']
                data['ladder_id'] = oldData['ladder_id']
                data['last_active_season'] = oldData['last_active_season']
                data['league_tier'] = oldData['league_tier']
                data['race'] = (player['member'][0]
                                ['played_race_count'][0]
                                ['race']['en_US'])
                data['wins'] = player['wins']
                data['losses'] = player['losses']
                data['ties'] = player['ties']
                data['current_win_streak'] = player['current_win_streak']
                # data['join_time_stamp'] = player['join_time_stamp']
                data['last_played'] = datetime.fromtimestamp(
                    player['last_played_time_stamp'])
                data['refreshed'] = jsonData['request_datetime']

                if(data['race'] == oldData['race']):
                    return data

    def processGames(self, oldData, newData):
        """Process data and look for new matches."""
        wins = newData['wins'] - oldData['wins']
        losses = newData['losses'] - oldData['losses']
        ties = newData['ties'] - oldData['ties']
        noGames = wins + losses + ties

        if oldData['mmr'] == 0:
            oldData['mmr'] = newData['mmr']
            new = True
        else:
            new = False

        if noGames == 1:
            # Only one game since last checked -> 100% confidence
            logger.info("{}: Single game!".format(oldData['ID']))
            result = wins - losses
            try:
                delta = newData['last_played'] - oldData['last_played']
            except Exception:
                delta = 60 * 10
            max_length = delta.total_seconds()
            self.insertGame(oldData['ID'], result, newData['last_played'],
                            newData['mmr'],
                            newData['mmr'] - oldData['mmr'],
                            False, max_length)
        else:
            # More than one game -> need to guess mmr change of the games
            self.guessGames(oldData, newData, new)

        # Initiate refresh of meta data
        self.controller.metaQueue.put(oldData['ID'])

    def requestMatchHistory(self, id, name, realm=1):
        """Get match history of a player."""
        matches = []

        # Blizzard has an encoding bug in this part of their api;
        # trying to reproduce this bug
        names = [name, name.encode("utf-8").decode('iso-8859-1')]

        # Some player have a different realms (most 1, some 2; is 3+ possible?)
        possible_realms = [1, 2, 3]

        realms = [realm]

        for realm in possible_realms:
            realms.append(realm)

        for name, realm in product(names, realms):
            params = urllib.parse.urlencode(self.controller.sc2ApiParams)
            url = "https://eu.api.battle.net/sc2/profile/{}/{}/{}/matches?{}"
            url = url.format(
                id, realm, name, params)
            jsonData, status = self.controller.performApiRequest(url)
            # Player found.
            if status == 200:
                break
            # Try other options.
            elif status == 404:
                continue
            # Internal Server Error - no matches will be available
            elif status == 500:
                return matches
            else:
                raise Exception('Request Error {} for {}'.format(status, url))

        for match in jsonData['matches']:
            if match['type'] == 'SOLO':
                if match['decision'] == "WIN":
                    result = 1
                elif match['decision'] == "LOSS":
                    result = -1
                else:
                    result = 0
                matches.append({'date': datetime.fromtimestamp(
                    match['date']), 'result': result})

        return matches

    def guessGames(self, oldData, newData, new):
        """Guess order, time and mmr change of games"""
        """ if more than one game was played."""
        matchHistory = self.requestMatchHistory(
            newData['sc2_player_id'],
            newData['sc2_name'].split("#")[0],
            newData['realm'])
        wins = newData['wins'] - oldData['wins']
        losses = newData['losses'] - oldData['losses']
        ties = newData['ties'] - oldData['ties']
        noGames = wins + losses + ties
        logger.info(
            "{}: {} games - guessing...".format(oldData['ID'], noGames))

        matches = []
        wins_found = 0
        losses_found = 0
        ties_found = 0
        last_played = newData['last_played']

        # Match history last_played date might differ(?) by a few seconds from
        # ladder api data last_played. Adjust by using a buffer of 10 seconds:
        buffer = timedelta(seconds=10)

        # Check if the most recent game lacks behind in the match history
        if (len(matchHistory) == 0 or
                matchHistory[0]['date'] < newData['last_played'] - buffer):
            if wins > wins_found and newData['current_win_streak'] > 0:
                wins_found += 1
                matches.append({'date': newData['last_played'], 'result': 1})
            elif losses > losses_found and newData['current_win_streak'] == 0:
                # Winstreak does not tell if last match could have been a tie.
                # Guess that is was a loss first.
                losses_found += 1
                matches.append({'date': newData['last_played'], 'result': -1})
            elif ties > ties_found and newData['current_win_streak'] == 0:
                ties_found += 0
                matches.append({'date': newData['last_played'], 'result': 0})
            else:
                logger.warning((
                    "{}: Most recent game is missing in match history,"
                    " but does not fit in.").format(oldData['ID']))

        # Search for the matches in match history (last 25 games, including
        # custom games, team games, unranked, offrace) that  fit to the
        # missing data. If there are more wins/losses/ties in the relevant
        # time frame guess that it are the most recent games of this type.
        for match in matchHistory:
            if(match['date'] <= newData['last_played'] + buffer and
               (oldData['last_played'] is not None and
                    match['date'] > oldData['last_played'] - buffer)):
                if match['result'] > 0 and wins_found < wins:
                    wins_found += 1
                elif match['result'] < 0 and losses_found < losses:
                    losses_found += 1
                elif match['result'] == 0 and ties_found < ties:
                    ties_found += 1
                else:
                    continue
                matches.append(match)

            last_played = match['date']

        missing_games = noGames - wins_found - losses_found - ties_found

        if missing_games > 0 and not new:
            # If a player isn't new in the database and has played more
            # than 25 games since the last refresh or the match
            # history is not available for this player, there are
            # missing games in the match history. These are guessed to be very
            # close to the last game of the match history and in alternating
            # order.
            logger.info((
                "{}: {} missing games in match " +
                "history - more guessing!").format(
                oldData['ID'], missing_games))

            try:
                delta = (last_played - oldData['last_played']) / missing_games
            except Exception:
                delta = timedelta(minutes=3)

            if delta > timedelta(minutes=3):
                delta = timedelta(minutes=3)

            while (wins_found < wins or
                   losses_found < losses or
                   ties_found < ties):

                if wins_found < wins:
                    last_played = last_played - delta
                    matches.append({'date': last_played, 'result': 1})
                    wins_found += 1

                if (wins_found < wins and
                        wins - wins_found > losses - losses_found):
                    # If there are more wins than losses add
                    # a second win before the next loss.
                    last_played = last_played - delta
                    matches.append({'date': last_played, 'result': 1})
                    wins_found += 1

                if losses_found < losses:
                    # If there are more losses than wins add second loss before
                    # the next win.
                    last_played = last_played - delta
                    matches.append({'date': last_played, 'result': -1})
                    losses_found += 1

                if (losses_found < losses and
                        wins - wins_found < losses - losses_found):
                    # Add second lose
                    last_played = last_played - delta
                    matches.append({'date': last_played, 'result': -1})
                    losses_found += 1

                if ties_found < ties:
                    last_played = last_played - delta
                    matches.append({'date': last_played, 'result': 0})
                    ties_found += 1

        matches = sorted(matches, key=itemgetter('date'))

        MMR = oldData['mmr']
        totalMMRchange = newData['mmr'] - oldData['mmr']
        # Estimate MMR change to be +/-20 for a win and losse, each adjusted
        # by the average deviation to achive the most recent MMR value.
        # Is 20 accurate?
        MMRchange = 20

        while True:
            avgMMRadjustment = (totalMMRchange - MMRchange *
                                (wins - losses)) / (wins + losses)

            # Make sure that sign of MMR change is correct
            if abs(avgMMRadjustment) >= MMRchange and MMRchange <= 50:
                MMRchange += 1
                logger.info("{}: Adjusting avg. MMR change to {}".format(
                    oldData['ID'], MMRchange))
            else:
                break

        last_played = oldData['last_played']

        for idx, match in enumerate(matches):
            estMMRchange = round(
                MMRchange * match['result'] + avgMMRadjustment)
            MMR = MMR + estMMRchange
            try:
                delta = match['date'] - last_played
            except Exception:
                delta = timedelta(minutes=3)
            last_played = match['date']
            max_length = delta.total_seconds()
            # Don't mark the most recent game as guess, as time and mmr value
            # should be accurate (but not mmr change).
            guess = not (idx + 1 == len(matches))
            self.insertGame(oldData['ID'], match['result'],
                            match['date'], MMR, estMMRchange,
                            guess, max_length)

    def insertGame(self, playerID, result, played,
                   mmr, mmr_change, guess, max_length):
        """Insert a game into mysql table matchhistory."""
        inputData = {}
        inputData['playerID'] = playerID
        inputData['result'] = result
        inputData['played'] = played.strftime('%Y-%m-%d %H:%M:%S')
        inputData['mmr'] = mmr
        inputData['mmr_change'] = mmr_change
        inputData['guess'] = guess
        inputData['max_length'] = max(0, min(max_length, 65535))

        query, data = compose_mysql_insert_cmd('matchhistory', inputData)

        with self.controller.dbLock:
            with self.controller.db.cursor() as cursor:
                cursor.execute(query, data)
            self.controller.db.commit()


class MetaDataWorker(threading.Thread):
    """Worker to generate meta data."""

    def __init__(self, controller):
        """Init worker."""
        super().__init__()
        self.setDaemon(True)
        self.controller = controller
        self._stop_event = threading.Event()
        self.start()

    def stop(self):
        """Stop thread."""
        self._stop_event.set()

    def stopped(self):
        """Check if thread was stopped."""
        return self._stop_event.is_set()

    def run(self):
        """Run task."""
        while True:
            try:
                item = self.controller.metaQueue.get(timeout=3)
            except Empty:
                continue
            try:
                self.doWork(item)
            except Exception as e:
                logger.exception("message")
            finally:
                self.controller.metaQueue.task_done()

    def doWork(self, playerID):
        """Processs a playerID."""
        with self.controller.dbLock:
            # Delete old games:
            query = "DELETE FROM `{2}` WHERE `playerID` = {0}" +\
                    " AND ID NOT IN " +\
                    "( SELECT ID FROM " +\
                    "(SELECT ID FROM `{2}` " +\
                    "WHERE `playerID` = {0} " +\
                    "ORDER BY `played` DESC LIMIT {1}) " +\
                    "foo);"
            query = query.format(playerID,
                                 self.controller.config['no_games'],
                                 mysql_tables['matchhistory'])
            with self.controller.db.cursor() as cursor:
                cursor.execute(query)
            self.controller.db.commit()

            with self.controller.db.cursor() as cursor:
                query = (
                    "SELECT * FROM `{}` "
                    "WHERE `playerID` = {} ORDER BY `played` DESC LIMIT 100")
                cursor.execute(query.format(
                    mysql_tables['matchhistory'], playerID))
                matches = cursor.fetchall()
                rowcount = cursor.rowcount

            query = "SELECT ID FROM `{}` WHERE `playerID` = {} LIMIT 1".format(
                mysql_tables['metadata'],
                playerID)
            with self.controller.db.cursor() as cursor:
                cursor.execute(query)
                update = bool(cursor.rowcount)

        if rowcount > 0:

            input_data = self.analyzeMatches(matches)
            input_data['playerID'] = playerID

            if update:
                where = dict(playerID=playerID)
                query, data = compose_mysql_update_cmd(
                    'metadata', input_data, where)
            else:
                query, data = compose_mysql_insert_cmd('metadata', input_data)

            with self.controller.dbLock:
                with self.controller.db.cursor() as cursor:
                    cursor.execute(query, data)
                self.controller.db.commit()

    def analyzeMatches(self, matches):
        """Analyze matches statistically."""
        out = {}
        out['games_available'] = len(matches)
        out['current_mmr'] = matches[0]["mmr"]
        out['wma_mmr'] = 0.0
        wma_mmr_denominator = out['games_available'] * \
            (out['games_available'] + 1.0) / 2.0
        out['max_mmr'] = matches[0]["mmr"]
        out['min_mmr'] = matches[0]["mmr"]
        expected_mmr_value = 0.0
        expected_mmr_value2 = 0.0
        current_wining_streak = 0
        out['longest_wining_streak'] = 0
        current_losing_streak = 0
        out['longest_losing_streak'] = 0
        out['instant_left_games'] = 0
        out['guessed_games'] = 0
        out['wins'] = 0
        out['losses'] = 0
        out['ties'] = 0
        for idx, match in enumerate(matches):
            if match['result'] > 0:
                out['wins'] += 1
                current_wining_streak += 1
                current_losing_streak = 0
                if current_wining_streak > out['longest_wining_streak']:
                    out['longest_wining_streak'] = current_wining_streak
            elif match['result'] < 0:
                out['losses'] += 1
                current_losing_streak += 1
                current_wining_streak = 0
                if current_losing_streak > out['longest_losing_streak']:
                    out['longest_losing_streak'] = current_losing_streak
                if match['max_length'] <= 120:
                    out['instant_left_games'] += 1
            else:
                out['ties'] += 1
                current_wining_streak = 0
                current_losing_streak = 0

            if match['guess']:
                out['guessed_games'] += 1

            mmr = match["mmr"]
            out['wma_mmr'] += mmr * \
                (out['games_available'] - idx) / wma_mmr_denominator
            if out['max_mmr'] < mmr:
                out['max_mmr'] = mmr
            if out['min_mmr'] > mmr:
                out['min_mmr'] = mmr
            expected_mmr_value += mmr / out['games_available']
            expected_mmr_value2 += mmr * (mmr / out['games_available'])

        out['winrate'] = out['wins'] / out['games_available']

        if out['games_available'] <= 1:
            out['lr_mmr_slope'] = 0.0
            out['lr_mmr_intercept'] = expected_mmr_value
        else:
            ybar = expected_mmr_value
            xbar = -0.5 * (out['games_available'] - 1)
            numerator = 0
            denominator = 0
            for x, match in enumerate(matches):
                x = -x
                y = match['mmr']
                numerator += (x - xbar) * (y - ybar)
                denominator += (x - xbar) * (x - xbar)

            out['lr_mmr_slope'] = numerator / denominator
            out['lr_mmr_intercept'] = ybar - out['lr_mmr_slope'] * xbar

        out['sd_mmr'] = round(
            math.sqrt(expected_mmr_value2 -
                      expected_mmr_value *
                      expected_mmr_value))
        critical_idx = min(self.controller.config['no_critical_games'],
                           out['games_available']) - 1
        out['critical_game_played'] = matches[critical_idx]["played"]
        out['avg_mmr'] = expected_mmr_value

        return out
