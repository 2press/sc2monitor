"""Test the sc2monitor model."""
import pytest

from sc2monitor.model import League, Race, Result, Server


def test_result_win():
    assert Result.get('win') == Result.Win
    assert Result.get('Win') == Result.Win
    assert Result.get('WIN') == Result.Win
    assert Result.get('W') == Result.Win
    assert Result.get('w') == Result.Win
    assert Result.get(Result.Win) == Result.Win
    assert Result.get(1) == Result.Win
    assert Result.get(2) == Result.Win
    assert Result.Win.change() == 1
    assert Result.Win.short() == 'W'
    assert str(Result.Win) == 'Win'


def test_result_loss():
    assert Result.get('Loss') == Result.Loss
    assert Result.get('loss') == Result.Loss
    assert Result.get('LOSS') == Result.Loss
    assert Result.get('L') == Result.Loss
    assert Result.get('l') == Result.Loss
    assert Result.get(Result.Loss) == Result.Loss
    assert Result.get(-1) == Result.Loss
    assert Result.get(-2) == Result.Loss
    assert Result.Loss.change() == -1
    assert Result.Loss.short() == 'L'
    assert str(Result.Loss) == 'Loss'


def test_result_tie():
    assert Result.get('Tie') == Result.Tie
    assert Result.get('tie') == Result.Tie
    assert Result.get('TIE') == Result.Tie
    assert Result.get('T') == Result.Tie
    assert Result.get('t') == Result.Tie
    assert Result.get(Result.Tie) == Result.Tie
    assert Result.get(0) == Result.Tie
    assert Result.Tie.change() == 0
    assert Result.Tie.short() == 'D'
    assert str(Result.Tie) == 'Tie'


def test_result_unknown():
    assert Result.get('') == Result.Unknown
    assert Result.get(Result.Unknown) == Result.Unknown
    assert Result.get('unknown') == Result.Unknown
    assert Result.get('u') == Result.Unknown
    assert Result.get('U') == Result.Unknown
    assert Result.Unknown.change() == 0
    assert Result.Unknown.short() == 'U'
    assert str(Result.Unknown) == 'Unknown'
    assert Result.get('asdasda') == Result.Unknown


def test_race():
    def assert_race(race: str, assert_race: Race):
        race = race.lower()
        race_short = race[0]
        assert Race.get(race) == assert_race
        assert Race.get(race.upper()) == assert_race
        assert Race.get(race.capitalize()) == assert_race
        assert Race.get(race_short) == assert_race
        assert Race.get(race_short.upper()) == assert_race
        assert race_short.upper() == assert_race.short()
        assert race.capitalize() == str(assert_race)
        assert Race.get(assert_race) == assert_race

    assert_race('zerg', Race.Zerg)
    assert_race('protoss', Race.Protoss)
    assert_race('terran', Race.Terran)
    assert_race('random', Race.Random)
    assert Race.get('') == Race.Random

    with pytest.raises(ValueError):
        Race.get('Human')


def test_server():
    assert str(Server.America) == 'America'
    assert str(Server.Europe) == 'Europe'
    assert str(Server.Korea) == 'Korea'
    assert Server.America.short() == 'us'
    assert Server.Europe.short() == 'eu'
    assert Server.Korea.short() == 'kr'
    assert Server.America.id() == 1
    assert Server.Europe.id() == 2
    assert Server.Korea.id() == 3


def test_league():
    def assert_league(league: str, assert_league: League, ident: int):
        league = league.lower()
        league_short = league[0:2]
        assert League.get(league) == assert_league
        assert League.get(league.upper()) == assert_league
        assert League.get(league.capitalize()) == assert_league
        assert League.get(league_short) == assert_league
        assert League.get(league_short.upper()) == assert_league
        assert League.get(assert_league) == assert_league
        assert League.get(assert_league.value) == assert_league
        assert League.get(ident) == assert_league
        assert assert_league.id() == ident
        assert league.capitalize() == str(assert_league)
        if assert_league != League.Grandmaster:
            assert League.get(league[0]) == assert_league
            assert League.get(league[0].upper()) == assert_league
        else:
            assert League.get('GM') == assert_league
            assert League.get('gm') == assert_league

    assert_league('unranked', League.Unranked, -1)
    assert_league('bronze', League.Bronze, 0)
    assert_league('silver', League.Silver, 1)
    assert_league('gold', League.Gold, 2)
    assert_league('platinum', League.Platinum, 3)
    assert_league('diamond', League.Diamond, 4)
    assert_league('master', League.Master, 5)
    assert_league('grandmaster', League.Grandmaster, 6)

    assert League.get('') == League.Unranked
    with pytest.raises(ValueError):
        League.get('Test')
    with pytest.raises(ValueError):
        League.get(-2)
    with pytest.raises(ValueError):
        League.get(7)

    assert League.Master < League.Grandmaster
    assert League.Master <= League.Grandmaster
    assert League.Gold > League.Silver
    assert League.Gold >= League.Silver
    assert League.Diamond > League.Unranked
    assert League.Platinum >= League.Platinum

    with pytest.raises(TypeError):
        assert League.Master > 5
    with pytest.raises(TypeError):
        League.Master < 'Diamond' == NotImplemented
    with pytest.raises(TypeError):
        League.Master >= 5 == NotImplemented
    with pytest.raises(TypeError):
        League.Master <= 'Diamond' == NotImplemented
