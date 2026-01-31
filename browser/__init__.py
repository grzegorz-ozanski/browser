"""
    Browser module
"""
from .browser import Browser, PageElement
from .log import setup_logging, WebLogger
from .locator import Locator
from .manager import BrowserManager
from .options import BrowserOptions
from  .useragent import UserAgent

__all__ = [
    'Browser',
    'BrowserOptions',
    'BrowserManager',
    'Locator',
    'PageElement',
    'UserAgent',
    'WebLogger',
    'setup_logging',
]
