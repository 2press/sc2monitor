import pytest

from sc2monitor.model import Result

def test_result():
    assert Result.get('win') == Result.Win
