"""
    Browser module
"""
from .browser import Browser, PageElement
from .log import setup_logging
from .locator import Locator
from .manager import BrowserManager
from .options import BrowserOptions
from .weblogger import WebLogger

__all__ = [
    'Browser',
    'BrowserOptions',
    'BrowserManager',
    'WebLogger',
    'Locator',
    'PageElement',
    'setup_logging'
]
