"""
    Browser logging setup
"""
import logging
import os

from .logconfig import LOG_CONFIG


def _setup_handler(handler: logging.Handler,
                   level: str,
                   formatting: str) -> logging.Handler:
    """
        Configure a logging handler with predefined formatting.
    """
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
    log.setLevel(LOG_CONFIG.level)
    if log.hasHandlers():
        log.handlers.clear()
    handlers = []
    if LOG_CONFIG.console:
        handlers.append(_setup_handler(logging.StreamHandler(),
                                       LOG_CONFIG.level,
                                       LOG_CONFIG.formatting))
    if LOG_CONFIG.file:
        if not LOG_CONFIG.initialized and os.path.exists(LOG_CONFIG.file):
            os.remove(LOG_CONFIG.file)
        handlers.append(_setup_handler(logging.FileHandler(LOG_CONFIG.file, encoding='utf-8'),
                                       LOG_CONFIG.level,
                                       LOG_CONFIG.formatting))
    for handler in handlers:
        log.addHandler(handler)

    LOG_CONFIG.initialized = True
    return log
