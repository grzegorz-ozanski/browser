"""
    Browser logging setup
"""
import logging
import os
from dataclasses import dataclass, field
from distutils.util import strtobool
from typing import Any, Generic, TypeVar

T = TypeVar('T', bound=Any)


@dataclass
class EnvironmentValue(Generic[T]):
    """
    Cached environment value
    """
    env_key: str
    default: T
    _value: T | None = None
    _value_type: type = field(init=False)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __setattr__(self, key: str, value: object) -> None:
        if key == 'default':
            self._value_type = type(value)
        elif key == '_value' and self._value_type is bool and value is not None:
            value = bool(strtobool(str(value)))
        super().__setattr__(key, value)

    @property
    def value(self) -> T:
        """
        Get logger configuration item value

        :return: item value
        """
        if self._value is None:
            self._value = os.environ.get(self.env_key, self.default)
        return self._value


@dataclass
class LogConfig:
    """
    Logger configuration
    """
    level: EnvironmentValue[str] = field(
        default_factory=lambda: EnvironmentValue('PAYMENTS_LOG_LEVEL', 'DEBUG'))
    formatting: EnvironmentValue[str] = field(
        default_factory=lambda: EnvironmentValue('PAYMENTS_LOG_FORMATTING',
                                                 '%(levelname)s:%(name)s %(asctime)s %(message)s'))
    console: EnvironmentValue[bool] = field(
        default_factory=lambda: EnvironmentValue('PAYMENTS_LOG_TO_CONSOLE', True))
    file: EnvironmentValue[str] = field(
        default_factory=lambda: EnvironmentValue('PAYMENTS_LOG_FILENAME', ''))


LOG_CONFIG = LogConfig()


def _setup_handler(handler: logging.Handler,
                   level: str,
                   formatting: str) -> logging.Handler:
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(formatting))
    return handler


def setup_logging(name: str) -> logging.Logger:
    """
    Setup browser logging

    :param name: log name

    :return: logger object
    """
    log = logging.getLogger(name)
    log.setLevel(LOG_CONFIG.level.value)
    if log.hasHandlers():
        log.handlers.clear()
    handlers = []
    if LOG_CONFIG.console:
        handlers.append(_setup_handler(logging.StreamHandler(),
                                       LOG_CONFIG.level.value,
                                       LOG_CONFIG.formatting.value))
    if LOG_CONFIG.file:
        handlers.append(_setup_handler(logging.FileHandler(LOG_CONFIG.file.value),
                                       LOG_CONFIG.level.value,
                                       LOG_CONFIG.formatting.value))
    for handler in handlers:
        log.addHandler(handler)

    return log
