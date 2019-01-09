import pytest


def pytest_addoption(parser):
    parser.addoption("--apikey", action="store",
                     default='', help="bnet apikey")
    parser.addoption("--apisecret", action="store",
                     default='', help="bnet secret")


@pytest.fixture
def apikey(request):
    return request.config.getoption("--apikey")


@pytest.fixture
def apisecret(request):
    return request.config.getoption("--apisecret")
