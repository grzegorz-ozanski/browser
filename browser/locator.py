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
        return self.relative('..')

    def relative(self, rel_path: str) -> Self:
        """
        Return the locator relative to the current locator.
        :param rel_path: relative path
        :return: locator relative to the current locator
        """
        if self.type != By.XPATH:
            raise RuntimeError(f'Cannot create relative locator for non-XPATH locator {self}')
        return self.__class__(self.type, f'{self.value}/{rel_path}')

    def __repr__(self) -> str:
        """String representation of the locator."""
        return f'[({self.type}) {self.value}]'

