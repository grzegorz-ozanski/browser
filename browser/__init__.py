"""
    Browser module
"""
from .browser import Browser
from .locator import Locator
from .log import WebLogger, setup_logging, html_logger
from .manager import BrowserManager
from .options import BrowserOptions
from .page_element import PageElement
from .useragent import UserAgent

__all__ = [
    'Browser',
    'BrowserOptions',
    'BrowserManager',
    'Locator',
    'PageElement',
    'UserAgent',
    'WebLogger',
    'html_logger',
    'setup_logging'
]
