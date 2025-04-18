"""
    Browser logging setup
"""
import logging
from logging import Logger


def setup_logging(name: str, level: str, formatting: str = "%(levelname)s:%(name)s %(asctime)s %(message)s") -> Logger:
    """
    Setup browser logging

    :param name: log name
    :param level: log level name
    :param formatting: log format

    :return: logger object
    """
    log = logging.getLogger(name)
    log.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(formatting))
    log.addHandler(ch)
    return log
