"""
    Wrapper class for Selenium Webdriver
"""
import concurrent.futures
import os
import shutil
from datetime import datetime
from time import sleep, monotonic
from typing import Any, Callable, cast

from selenium.common.exceptions import (TimeoutException, StaleElementReferenceException,
                                        ElementClickInterceptedException, NoSuchElementException)
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement
# Intentionally choose to import expected_conditions as upper-case EC
# noinspection PyPep8Naming
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .locator import Locator
from .browseroptions import BrowserOptions
from .log import setup_logging

log = setup_logging(__name__)

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

class Browser(Chrome):
    """
    Chrome driver extension
    """

    def __init__(self, options: BrowserOptions):
        """

        :param options: Browser options
        """
        self.save_trace_logs = options.save_trace_logs
        self._default_timeout = options.timeout
        self.user_data_dir = options.user_data_dir
        self._error_log_dir = options.error_log_dir
        self.user_data_dir_delete_retries = 3
        self.user_data_dir_delete_retries_interval = 5
        self.dirty = False

        log.debug('Creating new Chrome instance with parameters: "%s"', options)

        chrome_options = Options()

        if options.driver_options:
            for opt in options.driver_options:
                chrome_options.add_argument(opt)
        if options.chrome_location:
            log.debug('Using Chrome from "%s"', options.chrome_location)
            chrome_options.binary_location = options.chrome_location
        if options.chromedriver_location:
            log.debug('Using Chromedriver from "%s"', options.chromedriver_location)
            service = Service(executable_path=options.chromedriver_location)
        else:
            service = None

        # supress mypy warning as service in WebDriver is actually defined as "service: Service = None"
        super().__init__(service=service, options=chrome_options)  # type: ignore[arg-type]
        # for headless mode, set window size at frist page open
        self.fix_window_size = any('headless' in arg for arg in chrome_options.arguments)
        self.set_page_load_timeout(options.timeout)

    def __del__(self) -> None:
        """
            Delete user profile if exists
        """
        if self.user_data_dir and self.user_data_dir.exists():
            for i in range(self.user_data_dir_delete_retries):
                try:
                    shutil.rmtree(self.user_data_dir)
                    break
                except PermissionError:
                    try:
                        sleep(self.user_data_dir_delete_retries_interval * 2**i)
                    except OSError:
                        pass

    @property
    def error_log_dir(self) -> str:
        """
        Directory for storing element error logs
        """
        return self._error_log_dir

    @error_log_dir.setter
    def error_log_dir(self, value: str) -> None:
        self._error_log_dir = value

    def click_page_element(self, locator: Locator,
                           timeout: int | None = None) ->None:
        """Click page element
        :param locator: element locator
        :param timeout: timeout or None if the default timeout should be used

        :raise NoSuchElementException if web element cannot be found
        """
        webelement = self.wait_for_page_element(locator, timeout)
        if not webelement:
            raise NoSuchElementException
        webelement.click()

    def click_element_using_js(self, element: WebElement) -> None:
        """
        Force click an element, ignoring any elements that may overlap it.

        :param element: WebElement to click
        """
        self._execute_javascript('arguments[0].click()', element)

    def click_element_with_retry(self, element: WebElement, by: str, value: str,
                                 timeout: int | None = None) -> None:
        """
        Try to click an element until it's neither overlapped nor refreshed by DOM change, or timeout expires.
        Ignores any ElementClickInterceptedException and StaleElementReferenceException unless timeout expires.
        :param element: element to click
        :param by: element locator strategy
        :param value: element locator value
        :param timeout: timeout or None if the default timeout should be used
        :raises TimeoutException if timeout expired
        """
        start = monotonic()
        exception_occurred = True
        while monotonic() - start < (timeout or self._default_timeout) and exception_occurred:
            log.debug('Pre element.click')
            try:
                exception_occurred = False
                element.click()
                log.debug('Post element.click')
            except ElementClickInterceptedException:
                log.debug('ElementClickInterceptedException occured while clicking %s', element)
                exception_occurred = True
                pass
            except StaleElementReferenceException:
                if (refreshed := self.wait_for_element(by, value, timeout)) is None:
                    raise TimeoutException(f'Timeout expired waiting for refreshed element ("{by}", "{value}")!')
                exception_occurred = True
                log.debug('StaleElementReferenceException occured while clicking %s', element)
                element = refreshed
            sleep(0.5)

    def click_element_with_retry_using_js(self, element: WebElement, by: str, value: str,
                                          timeout: int | None = None) -> None:
        """
        Force click an element, ignoring any elements that may overlap it.
        Searches for refreshed element if StaleElementReferenceException
        occurs during the click.

        :param element: WebElement to click
        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value
        :param timeout: timeout or None if the default timeout should be used
        """
        try:
            self.click_element_using_js(element)
        except StaleElementReferenceException:
            log.warning('Stale element exception occurred while trying to click (by=%s, value=%s)', by, value)
            refreshed = self.wait_for_element(by, value, timeout)
            if refreshed:
                self.click_element_using_js(refreshed)
            else:
                raise

    def click_page_element_with_retry(self, element: WebElement, locator: Locator,
                                      timeout: int | None = None) -> None:
        """
        Try to click an element until it's neither overlapped nor refreshed by DOM change, or timeout expires.
        Ignores any ElementClickInterceptedException and StaleElementReferenceException unless timeout expires.
        :param element: element to click
        :param locator: element locator
        :param timeout: timeout or None if the default timeout should be used
        :raises TimeoutException if timeout expired
        """
        self.click_element_with_retry(element, locator.type, locator.value, timeout)

    def click_page_element_with_retry_using_js(self, element: WebElement, locator: Locator,
                                               timeout: int | None = None) -> None:
        """
        Force click an element, ignoring any elements that may overlap it.
        If :param by and :param value are provided, the element will be searched for again if StaleElementReferenceException
        occurs during the click.

        :param element: WebElement to click
        :param locator: element locator
        :param timeout: timeout or None if the default timeout should be used
        """
        self.click_element_with_retry_using_js(element, locator.type, locator.value, timeout)

    def find_and_click_page_element_using_js(self, locator: Locator) -> None:
        """
        Finds and force click an element, ignoring any elements that may overlap it

        :param locator: locator
        """
        self.click_element_using_js(self.find_element(locator.type, locator.value))

    def find_page_element(self, locator: Locator) -> PageElement:
        """
        Finds page element

        :param locator: element to look for

        :return: PageElement found
        """
        return PageElement(self.find_element(locator.type, locator.value))

    def find_page_elements(self, locator: Locator) -> list[PageElement]:
        """
        Finds page elements

        :param locator: elements to look for

        :return: PageElements found
        """
        return [PageElement(element) for element in self.find_elements(locator.type, locator.value)]

    def get(self, url: str) -> None:
        """
        Opens provider URL. In headless mode, at first call also sets screen size to match window size
        :param url: URL to open
        """
        super().get(url)
        self.dirty = True
        if self.fix_window_size:
            window_size = self.get_window_size()
            self.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'width': 1280,
                'height': 800,
                'deviceScaleFactor': 1.25,
                'mobile': False,
                'screenWidth': window_size['width'],
                'screenHeight': window_size['height'],
                'screenOrientation': {  # optional
                    'angle': 0,
                    'type': 'landscapePrimary'
                }
            })
            self.fix_window_size = False

    def open_in_new_tab(self, url: str, close_old_tab: bool = True) -> None:
        """
        Opens URL in a new browser card

        :param url: an address of the page to open
        :param close_old_tab: close old tab (default: True)
        """
        try:
            old_tab = self.current_window_handle

            # Open a new empty card
            self._execute_javascript('window.open('');')

            # Switch to the new card (it's last on the card list)
            self.switch_to.window(self.window_handles[-1])
            self.get(url)

            # Close the old card, if requested
            if close_old_tab and old_tab != self.current_window_handle:
                self.switch_to.window(old_tab)
                self.close()

                # Switch to the card opened above
                self.switch_to.window(self.window_handles[-1])

        except Exception as e:
            print(f'Error navigating to "{url}": {e}')

    def safe_click(self, by: str, value: str,
                   timeout: int | None = None, ignore_exception: bool = False) -> None:
        """
        Wait until the provided WebElement becomes clickable, then click it and save its screenshot if the click fails

        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value
        :param timeout: timeout or None if default timeout should be used
        :param ignore_exception: raise exception if True, ignore if False (default: False)
        :raises any exception caused by element.click() if ignore_exception is set to False (default)
        """
        self.trace_click(
            self.wait_for_element_clickable(by, value, timeout), ignore_exception)

    def safe_click_page_element(self, locator: Locator,
                                timeout: int | None = None, ignore_exception: bool = False) -> None:
        """
        Wait until the provided WebElement becomes clickable, then click it and save its screenshot if the click fails

        :param locator: element locator
        :param timeout: timeout or None if default timeout should be used
        :param ignore_exception: raise exception if True, ignore if False (default: False)
        :raises any exception caused by element.click() if ignore_exception is set to False (default)
        """
        self.safe_click(locator.type, locator.value, timeout, ignore_exception)

    def trace_click(self, element: WebElement,
                    ignore_exception: bool = False) -> None:
        """
        Click the provided WebElement and save its screenshot if the click fails

        :param element: WebElement
        :param ignore_exception: raise exception if True, ignore if False (default: False)
        :raises any exception caused by element.click() if ignore_exception is set to False (default)
        """
        # we do want to create a trace dump on any exception
        # noinspection PyBroadException
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

    def wait_for_element(self, by: str, value: str,
                         timeout: int | None = None) -> WebElement | None:
        """
        Wait until all matching elements become visible, or timeout expires, then return the first one

        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value
        :param timeout: timeout or None if the default timeout should be used

        :return: WebElement found or None if timeout expired
        """
        items = self.wait_for_elements(by, value, timeout)
        return items[0] if items else None

    def wait_for_elements(self, by: str, value: str,
                          timeout: int | None = None) -> list[WebElement] | None:
        """
        Wait until all matching elements become visible, or the timeout expires

        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value
        :param timeout: timeout or None if the default timeout should be used

        :return: list of found WebElements or None if timeout expired
        """
        items = None
        timeout = timeout or self._default_timeout
        try:
            items = WebDriverWait(self, timeout).until(
                EC.visibility_of_all_elements_located((by, value)))
        except TimeoutException:
            pass
        return items

    def wait_for_element_clickable(self, by: str, value: str,
                                   timeout: int | None = None) -> WebElement:
        """
        Wait until a web element becomes clickable or the timeout expires

        :param by: locator strategy as provided in selenium.webdriver.common.by.By class
        :param value: locator value
        :param timeout: timeout or None if the default timeout should be used

        :return Clickable WebElement reference
        """
        timeout = timeout or self._default_timeout

        # 1. Wait for visibility
        WebDriverWait(self, timeout).until(
            EC.visibility_of_element_located((by, value))
        )

        # 2. Wait for clickability
        clickable = WebDriverWait(self, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

        # 3.Wait for not obscured
        WebDriverWait(self, timeout).until(
            self._is_not_obscured(clickable)
        )

        return clickable

    def wait_for_network_inactive(self, timeout: int | None = None) -> None:
        """
        Wait untli page is full loaded by checking if any network activity is stopped

        :param timeout: timeout or None if the default timeout should be used
        :return: anything returned by browser.execute_stript, or False if timeout occured
        """
        # Additional check for network activity
        timeout = timeout or self._default_timeout
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
        self._execute_javascript(network_idle_script)

        # Finally, wait a short time for any final rendering or initialization
        sleep(0.5)

    def wait_for_page_element(self, locator: Locator,
                              timeout: int | None = None) -> PageElement | None:
        """
        Wait until all matching elements become visible, or timeout expires, then return the first one

        :param locator: element to wait for
        :param timeout: timeout or None if the default timeout should be used

        :return: PageElement found or None if timeout expired
        """
        element = self.wait_for_element(locator.type, locator.value, timeout)
        return None if element is None else PageElement(element)

    def wait_for_page_element_clickable(self, locator: Locator,
                                        timeout: int | None = None) -> PageElement:
        """
        Wait until a web element becomes clickable or the timeout expires

        :param locator: element locator
        :param timeout: timeout or None if the default timeout should be used

        :return Clickable PageElement reference
        """
        element = self.wait_for_element_clickable(locator.type, locator.value, timeout)
        return None if element is None else PageElement(element)

    def wait_for_page_element_disappear(self, locator: Locator,
                                        timeout: int | None = None) -> None:
        """
        Wait until a web element disappears or timeout expires

        :param locator: element locator
        :param timeout: timeout or None if the default timeout should be used
        """
        WebDriverWait(self, timeout or self._default_timeout).until(
            EC.invisibility_of_element_located((locator.type, locator.value))
        )
        return None

    def wait_for_page_elements(self, page_elements: Locator,
                               timeout: int | None = None) -> list[PageElement] | None:
        """
        Wait until all matching elements become visible, or the timeout expires

        :param page_elements: elements to wait for
        :param timeout: timeout or None if the default timeout should be used

        :return: list of found PageElement or None if timeout expired
        """
        elements = self.wait_for_elements(page_elements.type, page_elements.value, timeout)
        return None if elements is None else [PageElement(element) for element in elements]

    def wait_for_page_inactive(self, timeout: int | None = None) -> Any:
        """
        Wait untli page is full loaded, more heavy version (DOM stopped changing)

        :param timeout: timeout or None if the default timeout should be used
        :return: anything returned by browser.execute_stript, or False if timeout occured
        """

        timeout = timeout or self._default_timeout
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
            future = executor.submit(self.execute_script, script)
            try:
                return future.result(timeout=timeout + 2)
            except concurrent.futures.TimeoutError:
                log.debug(f'Timeout {timeout}(s) expired waiting for page to become inactive!')
                return False

    def wait_for_page_load_completed(self) -> None:
        """
        Wait untli page is full loaded, the lightest version (document ready state is 'complete')
        """
        state = None
        while state != 'complete':
            state = self._execute_javascript('return document.readyState')
            log.debug(f'Page load state == {state}')
            sleep(0.1)

    def _execute_javascript(self, script: str, *args: Any) -> Any:
        """
        Wrapper for WebDriver.execute_script to satisfy 'mypy --scrict'
        :param script: script to execute
        :param args: script arguments
        :return: script result
        """
        # Ignore 'mypy --strict' error on a library function
        return self.execute_script(script, *args)  # type: ignore[no-untyped-call]

    @staticmethod
    def dump_element(element: WebElement | None) -> None:
        """
        Dump web element data
        :param element: WebElement
        """
        if element is None:
            return
        try:
            print(f'Tag name: {element.tag_name}')
            print(f'Text content: {element.text}')
            print(f'Attributes:')
            attributes = cast(list[dict[str, Any]], cast(object, element.get_property('attributes')))
            for attribute in attributes:
                print(f'  - {attribute["name"]} = {attribute["value"]}')
            print(f'Location on page: {element.location}')
            print(f'Size: {element.size}')
        except Exception as ex:
            print(f'Exception occured while gathering detailed information for element {element}. '
                  f'Details:\n{ex.__class__.__name__}:{str(ex)}')

    @staticmethod
    def safe_elements_list(unsafe_list: list[WebElement] | None) -> list[WebElement]:
        """
        Safely casts the list of WebElements which may also be None onto an actual list
        :param unsafe_list: input list
        :return: converted list
        :raise RuntimeError if :param unsafe_list is None
        """
        if unsafe_list is None:
            raise RuntimeError(f'Argument "unsafe_list" cannot be None!')
        return unsafe_list

    @staticmethod
    def safe_page_elements_list(unsafe_list: list[WebElement] | None) -> list[PageElement]:
        """
        Safely casts the list of WebElements which may also be None onto an actual list
        :param unsafe_list: input list
        :return: converted list
        :raise RuntimeError if :param unsafe_list is None
        """
        if unsafe_list is None:
            raise RuntimeError(f'Argument "unsafe_list" cannot be None!')
        return [PageElement(element) for element in unsafe_list]

    @staticmethod
    def _is_not_obscured(element: WebElement) -> Callable[['Browser'], bool | WebElement]:
        """
        Check if other elements do not overlap the provided one (i.e., the element is available for interaction)
        :param element: WebElement to check
        :return: Callable to use as predicate
        """

        def _check(browser: Browser) -> bool | WebElement:
            """
            Interanal function to be used as predicate for WebDriverWait
            :param browser: WebDriver object
            :return: Web element provided in "element" when becomes available for interaction
            """
            script = '''
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
            '''
            if browser._execute_javascript(script, element):
                return element
            return False

        return _check
