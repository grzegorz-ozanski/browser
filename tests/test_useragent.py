"""
    UserAgent class unittests
"""
import random

import pytest

from browser import UserAgent

PLATFORMS = [
    ('Linux', 'Windows'),
    ('Windows', 'Linux'),
]

CHROME_VERSION = '138.0.7204.49'

@pytest.fixture
def ua(platform: str) -> UserAgent:
    """
    UserAgent class fixture
    :param platform: platform name
    """
    return UserAgent(platform)


@pytest.fixture
def ua_rng(platform: str) -> UserAgent:
    """
    UserAgent class fixture with fixed random number generator
    :param platform: platform name
    """
    rng = random.Random(999)
    return UserAgent(platform, rng=rng)


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_default(platform: str, other: str, ua: UserAgent) -> None:
    assert platform in ua.default
    assert other not in ua.default


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_random(platform: str, other: str, ua: UserAgent) -> None:
    for _ in range(10):
        assert platform in ua.random
        assert other not in ua.random


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_initial_current_is_default(platform: str, other: str, ua: UserAgent) -> None:
    assert ua.current == ua.default
    assert other not in ua.current


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_next(platform: str, other: str, ua_rng: UserAgent) -> None:
    initial = ua_rng.current
    ua_rng.next()
    assert initial != ua_rng.current


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_reset(platform: str, other: str, ua_rng: UserAgent) -> None:
    initial = ua_rng.current
    ua_rng.next()
    assert initial != ua_rng.current
    ua_rng.reset()
    assert initial == ua_rng.current
    assert ua_rng.current == ua_rng.default


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_chromeversion_get(platform: str, other: str, ua: UserAgent) -> None:
    assert ua.chrome_version == CHROME_VERSION


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_chromeversion_set(platform: str, other: str, ua: UserAgent) -> None:
    chrome_version = '222.2.2222.22'
    ua.chrome_version = chrome_version
    assert ua.chrome_version == chrome_version
    ua.platform = other.lower()
    assert ua.chrome_version == CHROME_VERSION


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_chromeversion_invalid(platform: str, other: str, ua: UserAgent) -> None:
    ua._strings[platform.lower()][0] = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                                        'Chrome/xxx Safari/537.36')
    assert ua.chrome_version == '<invalid>'
