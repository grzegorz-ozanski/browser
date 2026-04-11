"""
    Default logger configuration, overridable with specified environment variables
"""
import logging
import os

from str_to_bool import str_to_bool


class LogConfig:
    """
        Configuration object for logging behavior and format.
    """

    def __init__(self) -> None:
        """
            Initialize the logging configuration with default values.
        """
        self._level = os.environ.get('BROWSER_LOG_LEVEL', 'DEBUG')
        self._formatting = os.environ.get('BROWSER_LOG_FORMATTING', '%(levelname)s:%(name)s %(asctime)s %(message)s')
        self._console = os.environ.get('BROWSER_LOG_TO_CONSOLE', 'True')
        self._file = os.environ.get('BROWSER_LOG_FILENAME', '')

    @property
    def console(self) -> bool:
        """
        :return: True if logs should be printed into the console (default), False otherwise
        """
        return bool(str_to_bool(self._console))

    @property
    def file(self) -> str:
        """
        :return: Log file name
        """
        return self._file

    @property
    def formatting(self) -> str:
        """
        :return: Logging formatting
        """
        return self._formatting

    @property
    def level(self) -> str:
        """
        :return: Logging level value
        """
        value = self._level
        if isinstance(logging.getLevelName(value), int):
            return value
        raise RuntimeError(f'Invalid log level specified in BROWSER_LOG_LEVEL: "{value}"')

    initialized: bool = False


LOG_CONFIG = LogConfig()
