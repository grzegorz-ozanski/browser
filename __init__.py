"""
    Browser module
"""
from .browser import Browser
from .browseroptions import BrowserOptions
from .log import setup_logging
from .page_element import PageElement
from .weblogger import WebLogger

__all__ = [
    "Browser",
    "BrowserOptions",
    "WebLogger",
    "PageElement",
    "setup_logging"
]
