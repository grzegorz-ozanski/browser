"""
    Log config tests
"""
import importlib

import pytest
from _pytest.monkeypatch import MonkeyPatch

from browser import logconfig


def test_invalid_log_level(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv('BROWSER_LOG_LEVEL', 'STACY')
    with pytest.raises(RuntimeError, match='Invalid log level specified in BROWSER_LOG_LEVEL: "STACY"'):
        importlib.reload(logconfig)
        _ = logconfig.LOG_CONFIG.level
