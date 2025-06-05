"""
    Default logger configuration, overridable with specified environment variables
"""
import logging
import os
from dataclasses import dataclass

from str_to_bool import str_to_bool


@dataclass
class EnvironmentValue:
    """
    Cached environment value
    """
    key: str
    default: str
    _value: str | None = None

    def __bool__(self) -> bool:
        """
            Return stored value as boolean
        """
        return bool(self.value)

    @property
    def value(self) -> str:
        """
        Get logger configuration item value, either from environment or from a cache
        :return: item value
        """
        if self._value is None:
            self._value = os.environ.get(self.key, self.default)
        return self._value


class LogConfig:
    """
        Configuration object for logging behavior and format.
    """

    def __init__(self) -> None:
        """
            Initialize the logging configuration with default values.
        """
        self._level = EnvironmentValue('BROWSER_LOG_LEVEL', 'DEBUG')
        self._formatting = EnvironmentValue('BROWSER_LOG_FORMATTING', '%(levelname)s:%(name)s %(asctime)s %(message)s')
        self._console = EnvironmentValue('BROWSER_LOG_TO_CONSOLE', 'True')
        self._file = EnvironmentValue('BROWSER_LOG_FILENAME', '')

    @property
    def console(self) -> bool:
        """
        :return: True if logs should be printed into console (default), False otherwise
        """
        return bool(str_to_bool(self._console.value))

    @property
    def file(self) -> str:
        """
        :return: Log file name
        """
        return self._file.value

    @property
    def formatting(self) -> str:
        """
        :return: Logging formatting
        """
        return self._formatting.value


    @property
    def level(self) -> str:
        """
        :return: Logging level value
        """
        value = self._level.value
        if isinstance(logging.getLevelName(value), int):
            return value
        raise RuntimeError(f'Invalid log level specified in {self._level.key}: "{value}"')
    initialized: bool = False


LOG_CONFIG = LogConfig()
