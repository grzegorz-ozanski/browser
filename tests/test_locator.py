"""
    Locator tests
"""
from selenium.webdriver.common.by import By

from browser import Locator


def test_locator() -> None:
    locator = Locator(By.ID, 'foo')
    assert str(locator) == f'[({By.ID}) foo]'
