"""Test the sc2monitor model."""
from sc2monitor.model import League, Race, Result


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


def test_race():
    def assert_race(race: str, assert_race: Race):
        race = race.lower()
        race_short = race[0]
        assert Race.get(race) == assert_race
        assert Race.get(race.upper()) == assert_race
        assert Race.get(race.capitalize()) == assert_race
        assert Race.get(race_short) == assert_race
        assert Race.get(race_short.upper()) == assert_race
        assert Race.get(assert_race) == assert_race

    assert_race('zerg', Race.Zerg)
    assert_race('protoss', Race.Protoss)
    assert_race('terran', Race.Terran)
    assert_race('random', Race.Random)
    assert Race.get('') == Race.Random


def test_league():
    def assert_league(league: str, assert_league: League):
        league = league.lower()
        league_short = league[0:2]
        assert League.get(league) == assert_league
        assert League.get(league.upper()) == assert_league
        assert League.get(league.capitalize()) == assert_league
        assert League.get(league_short) == assert_league
        assert League.get(league_short.upper()) == assert_league
        assert League.get(assert_league) == assert_league
        assert League.get(assert_league.value) == assert_league
        if assert_league != League.Grandmaster:
            assert League.get(league[0]) == assert_league
            assert League.get(league[0].upper()) == assert_league
        else:
            assert League.get('GM') == assert_league
            assert League.get('gm') == assert_league

    assert_league('unranked', League.Unranked)
    assert_league('bronze', League.Bronze)
    assert_league('silver', League.Silver)
    assert_league('gold', League.Gold)
    assert_league('platinum', League.Platinum)
    assert_league('diamond', League.Diamond)
    assert_league('master', League.Master)
    assert_league('grandmaster', League.Grandmaster)
