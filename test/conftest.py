import pytest


def pytest_addoption(parser):
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
                     default='mysql+pymsql', help="database protocol")


@pytest.fixture
def apikey(request):
    return request.config.getoption("--apikey")


@pytest.fixture
def apisecret(request):
    return request.config.getoption("--apisecret")


@pytest.fixture
def db(request):
    return request.config.getoption("--db")


@pytest.fixture
def user(request):
    return request.config.getoption("--user")


@pytest.fixture
def passwd(request):
    return request.config.getoption("--passwd")


@pytest.fixture
def protocol(request):
    return request.config.getoption("--protocol")
