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


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_default(platform: str, other: str) -> None:
    ua = UserAgent(platform)
    assert platform in ua.default
    assert other not in ua.default


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_random(platform: str, other: str) -> None:
    ua = UserAgent(platform)
    for _ in range(10):
        assert platform in ua.random
        assert other not in ua.random


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_initial_current_is_default(platform: str, other: str) -> None:
    ua = UserAgent(platform)
    assert ua.current == ua.default
    assert other not in ua.current


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_next(platform: str, other: str) -> None:
    rng = random.Random(999)
    ua = UserAgent(platform, rng=rng)
    initial = ua.current
    ua.next()
    assert initial != ua.current


@pytest.mark.parametrize('platform, other', PLATFORMS)
def test_reset(platform: str, other: str) -> None:
    rng = random.Random(999)
    ua = UserAgent(platform, rng=rng)
    initial = ua.current
    ua.next()
    assert initial != ua.current
    ua.reset()
    assert initial == ua.current
    assert ua.current == ua.default
