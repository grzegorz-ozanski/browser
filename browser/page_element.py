"""
    Wrapper class for selenium.webdriver.remote.webelement.WebElement which allows to use an API
    consintent with the one of a Browser (find_page_element(s) methods accepting argument of type Locator)
"""
from selenium.webdriver.remote.webelement import WebElement

from .locator import Locator


class PageElement(WebElement):
    def __init__(self, element: WebElement) -> None:
        super().__init__(element.parent, element._id)

    def find_page_element(self, locator: Locator) -> 'PageElement':
        """
        Finds page element

        :param locator: element to look for

        :return: WebElement found
        """
        return PageElement(self.find_element(locator.type, locator.value))

    def find_page_elements(self, locator: Locator) -> list['PageElement']:
        """
        Finds page elements

        :param locator: elements to look for

        :return: PageElements found
        """
        return [PageElement(element) for element in self.find_elements(locator.type, locator.value)]
