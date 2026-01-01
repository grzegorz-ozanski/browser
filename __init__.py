"""
    Browser module
"""
from .browser import Browser, PageElement
from .browseroptions import BrowserOptions
from .log import setup_logging
from .locator import Locator
from .weblogger import WebLogger

__all__ = [
    'Browser',
    'BrowserOptions',
    'WebLogger',
    'Locator',
    'PageElement',
    'setup_logging'
]
