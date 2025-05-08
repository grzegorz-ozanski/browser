"""
    Wrapper class for Selenium Webdriver
"""
import concurrent.futures
import os
from datetime import datetime
from time import sleep
from typing import Any, Callable

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Remote, Chrome, ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .log import setup_logging

log = setup_logging(__name__)


def _browser_factory(webdriver_class: type[Chrome | Remote],
                     url: str,
                     options: list[str],
                     binary_location: str) -> Chrome | Remote:
    """
    Create webriver instance of a specified class

    :param webdriver_class: webdriver class (either Chrome or Remote)
    :param url: webdriver URL (link ot a running instance or path to the executable)
    :param options: webdriver options
    :param binary_location: webdriver binary location

    :return: webdriver object instance
    """
    if options is None:
        options = []

    driver_options = Options()

    # for multimedia service login error in headless mode
    options.append(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36")
    for opt in options:
        driver_options.add_argument(opt)
    if binary_location:
        driver_options.binary_location = binary_location
    if url:
        service = Service(executable_path=url)
    else:
        service = None
    driver = webdriver_class(service=service, options=driver_options)
    return driver


# noinspection PyMissingConstructor
class BrowserBase(WebDriver):
    """
    Web driver extension class - base
    """

    def __init__(self, timeout: int):
        self.browser = None
        self._default_timeout = timeout
        self._error_log_dir = "."

    @property
    def error_log_dir(self) -> str:
        """
        Directory for storing element error logs
        """
        return self._error_log_dir

    @error_log_dir.setter
    def error_log_dir(self, value: str):
        self._error_log_dir = value

    @staticmethod
    def _is_not_obscured(element: WebElement) -> Callable[[WebDriver], bool | WebElement]:
        """
        Check if element is not overlapped by other (i.e. available for interaction)
        :param element: WebElement to check
        :return: Callable to use as predicate
        """

        def _check(browser: WebDriver) -> bool | WebElement:
            """
            Check if element is not overlapped by other (i.e. available for interaction)
            :param browser: WebDriver object
            :return: Web element provided in "element" when becomes available for interaction
            """
            script = """
                const element = arguments[0];
                const rect = element.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;

                // Get the element at the center point
                const elementAtPoint = document.elementFromPoint(centerX, centerY);
                
                // Check if either element or elementAtPoint is null
                if (element && elementAtPoint) {
                    // Check if the element or one of its descendants is at that point
                    return (elementAtPoint === element) || element.contains(elementAtPoint) || elementAtPoint.contains(element);
                } else {
                    return false;
                }
            """
            if browser.execute_script(script, element):
                return element
            return False

        return _check

    def wait_for_page_load_completed(self) -> None:
        """
        Wait untli page is full loaded, lightest version (document ready state is 'complete')
        """
        state = None
        while state != 'complete':
            state = self.browser.execute_script('return document.readyState')
            log.debug(state)
            sleep(0.1)

    def wait_for_page_inactive(self, timeout: int | None = None) -> Any:
        """
        Wait untli page is full loaded, more heavy version (DOM stopped changing)

        :param timeout: timeout or None if default timeout should be used
        :return: anything returned by browser.execute_stript, or False if timeout occured
        """

        timeout = self._default_timeout if timeout is None else timeout
        script = '''
            return new Promise(resolve => {
                const observer = new MutationObserver(mutations => {
                    // Use a timer to detect when mutations have stopped for 1 second
                    if (window._mutationTimer) {
                        clearTimeout(window._mutationTimer);
                    }
                    window._mutationTimer = setTimeout(() => {
                        observer.disconnect();
                        resolve(true);
                    }, 1000);
                });
                observer.observe(document.body, {
                    childList: true, 
                    attributes: true,
                    subtree: true
                });
                // Set a timeout for the maximum wait time
                setTimeout(() => {
                    observer.disconnect();
                    resolve(false);
                }, ''' + str(timeout * 1000) + ''');
            });
        '''
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.browser.execute_script, script)
            try:
                return future.result(timeout=timeout + 2)
            except concurrent.futures.TimeoutError:
                log.debug(f'Timeout {timeout}(s) expired waiting for page to become inactive!')
                return False

    def wait_for_network_inactive(self, timeout: int | None = None) -> None:
        """
        Wait untli page is full loaded by checking if any network activity is stopped

        :param timeout: timeout or None if default timeout should be used
        :return: anything returned by browser.execute_stript, or False if timeout occured
        """
        # Additional check for network activity
        timeout = self._default_timeout if timeout is None else timeout
        network_idle_script = '''
            return new Promise(resolve => {
                // Use Performance API to check if resources are still loading
                let lastResourceCount = performance.getEntriesByType('resource').length;

                const checkResources = () => {
                    const currentCount = performance.getEntriesByType('resource').length;
                    if (currentCount === lastResourceCount) {
                        // No new resources in the last second
                        resolve(true);
                    } else {
                        lastResourceCount = currentCount;
                        setTimeout(checkResources, 1000);
                    }
                };

                setTimeout(checkResources, 1000);
                // Fallback timeout
                setTimeout(() => resolve(false), ''' + str((timeout - 4) * 1000) + ''');
            });
        '''
        self.browser.execute_script(network_idle_script)

        # Finally, wait a short time for any final rendering or initialization
        sleep(0.5)

    def wait_for_elements(self, by: str, value: str, timeout: int | None = None) -> list[WebElement] | None:
        """
        Wait until all matching elements become visible, or timeout expires

        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value
        :param timeout: timeout or None if default timeout should be used

        :return: list of found WebElements or None if timeout expired
        """
        items = None
        timeout = self._default_timeout if timeout is None else timeout
        try:
            items = WebDriverWait(self, timeout).until(
                EC.visibility_of_all_elements_located((by, value)))
        except TimeoutException:
            pass
        return items

    def wait_for_element(self, by: str, value: str, timeout=None) -> WebElement:
        """
        Wait until all matching elements become visible, or timeout expires, then return the first one

        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value
        :param timeout: waiting timeout

        :return: WebElement found or None if timeout expired
        """
        items = self.wait_for_elements(by, value, timeout)
        return items[0] if items is not None else None

    def click_element_with_js(self, element: WebElement) -> None:
        """
        Force click element, ignoring any elements that may overlap it

        :param element: WebElement to click

        """
        self.browser.execute_script('arguments[0].click()', element)

    def find_and_click_element_with_js(self, by: str, value: str) -> None:
        """
        Force click element, ignoring any elements that may overlap it

        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value

        """
        self.click_element_with_js(self.browser.find_element(by, value))

    def trace_click(self, element: WebElement, ignore_exception: bool = False) -> None:
        """
        Click provided WebElement and save its screenshot if click fails

        :param element: WebElement
        :param ignore_exception: raise exception if True, ignore if False (default: False)
        :raises any exception caused by element.click() if ignore_exception is set to False (default)
        """
        try:
            element.click()
        except Exception:
            timestamp = datetime.today().isoformat(sep=' ', timespec='milliseconds').replace(':', '-')
            file_name = f'{timestamp} {element.tag_name} error.png'
            os.makedirs(self.error_log_dir, exist_ok=True)
            element.screenshot(os.path.join(self.error_log_dir, file_name))
            print('Error clicking element:')
            print(f'Tag: {element.tag_name}')
            print(f'HTML: {element.get_attribute("outerHTML")}')
            print(f'Text: {element.text}')
            if not ignore_exception:
                raise

    def safe_click(self, by: str, value: str, timeout: int | None = None, ignore_exception: bool = False) -> None:
        """
        Wait until provided WebElement becomes clickable, then click it and save its screenshot if click fails

        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value
        :param timeout: timeout or None if default timeout should be used
        :param ignore_exception: raise exception if True, ignore if False (default: False)
        :raises any exception caused by element.click() if ignore_exception is set to False (default)
        """
        self.trace_click(
            self.wait_for_element_clickable(by, value, timeout), ignore_exception)

    def wait_for_element_disappear(self, by: str, value: str, timeout: int | None = None) -> bool | WebElement:
        """
        Wait until web element disappear or timeout expires

        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value
        :param timeout: timeout or None if default timeout should be used
        """
        return WebDriverWait(self.browser, self._default_timeout if timeout is None else timeout).until(
            EC.invisibility_of_element_located((by, value))
        )

    def wait_for_element_clickable(self, by: str, value: str, timeout: int | None = None) -> bool | WebElement:
        """
        Wait until web element becomes clickable or timeout expires

        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value
        :param timeout: timeout or None if default timeout should be used

        :return Clickable WebElement reference
        """
        timeout = self._default_timeout if timeout is None else timeout

        return WebDriverWait(self.browser, timeout).until(
            self._is_not_obscured(
                WebDriverWait(self.browser, timeout).until(
                    EC.element_to_be_clickable(WebDriverWait(self.browser, timeout).until(
                        EC.visibility_of_element_located((by, value))
                    ))
                )
            )
        )

    def open_dropdown_menu(self, by: str, value: str) -> None:
        """
        Opens dropdown menu
        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value
        """
        ActionChains(self.browser).move_to_element(self.wait_for_element(by, value)).perform()

    def force_get(self, url: str, close_old_tab: bool = True):
        """
        Opens URL in a new browser card

        :param url: address
        :param close_old_tab: close old tab (default: True)
        """
        try:
            old_tab = self.browser.current_window_handle

            # Open a new empty card
            self.browser.execute_script('window.open('');')

            # Switch to the new card (it's last on the card list)
            self.browser.switch_to.window(self.browser.window_handles[-1])
            self.browser.get(url)

            # Close the old card, if requested
            if close_old_tab and old_tab != self.browser.current_window_handle:
                self.browser.switch_to.window(old_tab)
                self.browser.close()

                # Switch to the card opened above
                self.browser.switch_to.window(self.browser.window_handles[-1])

        except Exception as e:
            print(f'Error navigating to "{url}": {e}')

    @staticmethod
    def dump_element(element: WebElement | None) -> None:
        """
        Dump web element data
        :param element: WebElement
        """
        if element is None:
            return
        try:
            print(f"Tag name: {element.tag_name}")
            print(f"Text content: {element.text}")
            print(f"Attributes:")
            for attribute in element.get_property('attributes'):
                # noinspection PyTypeChecker
                print(f"  - {attribute['name']} = {attribute['value']}")
            print(f"Location on page: {element.location}")
            print(f"Size: {element.size}")
        except Exception as ex:
            print(f"Exception occured while gathering detailed information for element {element}. "
                  f"Details:\n{ex.__class__.__name__}:{str(ex)}")


class Browser(BrowserBase):
    """
    Web driver extension class - actual extension. Allows seamless access to both WebDriver
    and WebDriver extension class attributes
    """

    def __init__(self, url: str = 'http://127.0.0.1:9515',
                 timeout: int = 10,
                 options: list[str] | None = None,
                 binary_location: str = '',
                 save_trace_logs=False):
        super().__init__(timeout)
        self.save_trace_logs = save_trace_logs
        protocol = url.split('://')

        if protocol[0] == 'http':
            log.debug(f'Creating new Browser instance with parameters: "{url=}", "{timeout=}", "{options=}"')
            self.browser = _browser_factory(Remote, url, options, binary_location)
        elif protocol[0] == 'file':
            log.debug(f'Creating new Browser instance with parameters: "<Chrome>", "{timeout=}", "{options=}"')
            self.browser = _browser_factory(Chrome, protocol[1], options, binary_location)
        else:
            raise Exception(f'Unknown protocol: "{protocol[0]}"')

    def __getattribute__(self, attribute: str) -> Any:
        """
        Try to find the requested attribute first in extension class; if missing,
        fall back to stored WebDriver class instance

        :param attribute: attribute name

        :return: attribute value found in either parent BrowserBase class or in stored WebDriver instance

        :raises: AttributeError if attribute cannot be found in either locations above
        """
        try:
            return super().__getattribute__(attribute)
        except AttributeError:
            try:
                return self.browser.__getattribute__(attribute)
            except AttributeError:
                raise AttributeError(f"Neither '{self.__class__.__name__}' nor '{self.browser.__class__.__name__}' "
                                     f"object has an attribute '{attribute}' ")
