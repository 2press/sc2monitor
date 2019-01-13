"""Configure pytest input paramters."""
import pytest


def pytest_addoption(parser):
    """Add options to pytest parser."""
    parser.addoption("--apikey", action="store",
                     default='', help="bnet apikey")
    parser.addoption("--apisecret", action="store",
                     default='', help="bnet secret")
    parser.addoption("--db", action="store",
                     default='localhost', help="database address")
    parser.addoption("--user", action="store",
                     default='sc2monitor', help="database user")
    parser.addoption("--passwd", action="store",
                     default='', help="database password")
    parser.addoption("--protocol", action="store",
                     default='sqlite',
                     help="database protocol (mysql+pymysql, sqlite, ...)")


@pytest.fixture
def apikey(request):
    """Return API key."""
    return request.config.getoption("--apikey")


@pytest.fixture
def apisecret(request):
    """Return API key."""
    return request.config.getoption("--apisecret")


@pytest.fixture
def db(request):
    """Return API secret."""
    return request.config.getoption("--db")


@pytest.fixture
def user(request):
    """Return db user."""
    return request.config.getoption("--user")


@pytest.fixture
def passwd(request):
    """Return db password."""
    return request.config.getoption("--passwd")


@pytest.fixture
def protocol(request):
    """Return dp protocol."""
    return request.config.getoption("--protocol")
