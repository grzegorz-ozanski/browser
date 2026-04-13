"""
    Web page element locator module
"""
from dataclasses import dataclass
from typing import Self

from selenium.webdriver.common.by import By


@dataclass
class Locator:
    """Element locator used for finding inputs and buttons in the page."""
    type: str
    value: str

    def parent(self) -> Self:
        """
        Returns the parent element of the locator for XPATH locators
        :return: element's parent
        """
        if self.type != By.XPATH:
            raise RuntimeError(f'Cannot find parent for non-XPATH locator {self}')
        return self.__class__(self.type, f'{self.value}/..')

    def __repr__(self) -> str:
        """String representation of the locator."""
        return f'[({self.type}) {self.value}]'
