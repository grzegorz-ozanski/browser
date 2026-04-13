"""
    Wrapper class for Selenium Webdriver
"""
import os
import signal
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from time import sleep, monotonic
from typing import Any, Callable, cast

from selenium.common.exceptions import (TimeoutException, StaleElementReferenceException,
                                        ElementClickInterceptedException, NoSuchElementException,
                                        WebDriverException)
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement
# Intentionally choose to import expected_conditions as upper-case EC
# noinspection PyPep8Naming
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .locator import Locator
from .log import setup_logging
from .options import BrowserOptions
from .page_element import PageElement

log = setup_logging(__name__)

class Browser(Chrome):
    """
    Chrome driver extension
    """

    def __init__(self, options: BrowserOptions):
        """

        :param options: Browser options
        """
        self.options = options
        self._assert_profile_free()
        self.dirty = False
        self.debug_clicks = os.getenv('PAYMENTS_DEBUG_CLICK', '0') == '1'
        self.debug_click_focus = os.getenv('PAYMENTS_DEBUG_CLICK_FOCUS', '0') == '1'

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

    @property
    def error_log_dir(self) -> str:
        """
        Directory for storing element error logs
        """
        return self.options.error_log_dir

    @error_log_dir.setter
    def error_log_dir(self, value: str) -> None:
        self.options.error_log_dir = value

    @property
    def timezone(self) -> str:
        """
        Get browser timezone
        :return: Timezone string
        """
        return str(self._execute_javascript("return Intl.DateTimeFormat().resolvedOptions().timeZone"))

    def click_page_element(self, locator: Locator,
                           timeout: int | None = None) -> None:
        """
        Click an element in the page
        :param locator: element locator
        :param timeout: timeout or None if the default timeout should be used

        :raise NoSuchElementException if web element cannot be found
        """
        webelement = self.wait_for_page_element(locator, timeout)
        if not webelement:
            raise NoSuchElementException
        self._log_click_diagnostics('click_page_element:before', webelement)
        webelement.click()
        self._log_post_click_state('click_page_element:after')

    def click_element_using_js(self, element: WebElement) -> None:
        """
        Force click an element, ignoring any elements that may overlap it.

        :param element: WebElement to click
        """
        self._log_click_diagnostics('click_element_using_js:before', element)
        self._execute_javascript('arguments[0].click()', element)
        self._log_post_click_state('click_element_using_js:after')

    def click_page_element_using_js(self, locator: Locator) -> None:
        """
        Force click an element, ignoring any elements that may overlap it.

        :param locator: Locator to click
        """
        element = self.find_page_element(locator)
        self._log_click_diagnostics('click_element_using_js:before', element)
        self._execute_javascript('arguments[0].click()', element)
        self._log_post_click_state('click_element_using_js:after')

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
        while monotonic() - start < self._timeout(timeout) and exception_occurred:
            log.debug('Pre element.click')
            try:
                exception_occurred = False
                self._log_click_diagnostics('click_element_with_retry:before', element)
                element.click()
                log.debug('Post element.click')
                self._log_post_click_state('click_element_with_retry:after')
            except ElementClickInterceptedException:
                log.debug('ElementClickInterceptedException occured while clicking %s', element)
                self._log_post_click_state('click_element_with_retry:intercepted')
                exception_occurred = True
                pass
            except StaleElementReferenceException:
                if (refreshed := self.wait_for_element(by, value, timeout)) is None:
                    raise TimeoutException(f'Timeout expired waiting for refreshed element ("{by}", "{value}")!')
                exception_occurred = True
                log.debug('StaleElementReferenceException occured while clicking %s', element)
                self._log_post_click_state('click_element_with_retry:stale')
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
        If :param by and :param value are provided, the element will be searched for again
        if StaleElementReferenceException occurs during the click.

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

    def quit(self) -> None:  # override
        """
        Force quit browser
        """
        old_handler = None
        try:
            if os.name != "nt":
                old_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

            # run 'quit()' in a thread with timeout
            exc: Exception | None = None

            def _do_quit() -> None:
                nonlocal exc
                try:
                    super(Browser, self).quit()
                except Exception as e:
                    exc = e

            t = threading.Thread(target=_do_quit, daemon=True)
            t.start()
            t.join(timeout=10)

            if t.is_alive():
                # fallback: kill chromedriver process tree (Windows)
                self._force_kill_driver_tree()

            if exc:
                raise exc

        finally:
            if old_handler is not None:
                signal.signal(signal.SIGINT, old_handler)

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
            self._log_click_diagnostics('trace_click:before', element)
            element.click()
            self._log_post_click_state('trace_click:after')
        except Exception:
            timestamp = datetime.today().isoformat(sep=' ', timespec='milliseconds').replace(':', '-')
            file_name = f'{timestamp} {element.tag_name} error.png'
            os.makedirs(self.error_log_dir, exist_ok=True)
            element.screenshot(os.path.join(self.error_log_dir, file_name))
            print('Error clicking element:')
            print(f'Tag: {element.tag_name}')
            print(f'HTML: {element.get_attribute("outerHTML")}')
            print(f'Text: {element.text}')
            self._log_post_click_state('trace_click:error')
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
        timeout = self._timeout(timeout)
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
        timeout = self._timeout(timeout)

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
        timeout = self._timeout(timeout)
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
                                        timeout: int | None = None) -> PageElement | None:
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
        WebDriverWait(self, self._timeout(timeout)).until(
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

        timeout = self._timeout(timeout)
        self.set_script_timeout(timeout + 2)

        script = """
        const done = arguments[arguments.length - 1];

        let finished = false;
        let quietTimer = null;

        function finish(result) {
            if (finished) return;
            finished = true;
            if (quietTimer) {
                clearTimeout(quietTimer);
            }
            observer.disconnect();
            done(result);
        }

        function armQuietTimer() {
            if (quietTimer) {
                clearTimeout(quietTimer);
            }
            quietTimer = setTimeout(() => finish(true), 1000);
        }

        const observer = new MutationObserver(() => {
            armQuietTimer();
        });

        observer.observe(document.body, {
            childList: true,
            attributes: true,
            subtree: true
        });

        // ważne: start liczenia ciszy od razu
        armQuietTimer();

        setTimeout(() => finish(false), %d);
        """ % (timeout * 1000)

        try:
            return bool(self.execute_async_script(script))
        except (TimeoutException, WebDriverException):
            log.debug("Timeout %d second(s) expired waiting for page to become inactive!", timeout)
            return False

    def wait_for_page_load_completed(self) -> None:
        """
        Wait untli page is full loaded, the lightest version (document ready state is 'complete')
        """
        state = None
        while state != 'complete':
            state = self._execute_javascript('return document.readyState')
            log.debug('Page load state == %s', state)
            sleep(0.1)

    def _assert_profile_free(self) -> None:
        """
        Check if Chrome profile is not locked
        :param profile_path: profile path
        """
        profile_path = Path(self.options.profile.path)
        lock_file = profile_path / "lockfile"

        if lock_file.exists():
            raise RuntimeError("Chrome profile is locked! "
                               "Probably previous Chrome instance is still running.")

    def _execute_javascript(self, script: str, *args: Any) -> Any:
        """
        Wrapper for WebDriver.execute_script to satisfy 'mypy --scrict'
        :param script: script to execute
        :param args: script arguments
        :return: script result
        """
        # Ignore 'mypy --strict' error on a library function
        return self.execute_script(script, *args)  # type: ignore[no-untyped-call]

    def _log_click_diagnostics(self, stage: str, element: WebElement) -> None:
        if not self.debug_clicks:
            return
        try:
            script = '''
                const element = arguments[0];
                const includeFocusState = arguments[1];
                const rect = element.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                const atPoint = document.elementFromPoint(centerX, centerY);
                const details = {
                    url: window.location.href,
                    readyState: document.readyState,
                    hasFocus: document.hasFocus(),
                    tagName: element.tagName,
                    text: element.innerText,
                    href: element.getAttribute('href'),
                    onclick: element.getAttribute('onclick'),
                    outerHTML: element.outerHTML,
                    rect: {
                        left: rect.left,
                        top: rect.top,
                        width: rect.width,
                        height: rect.height
                    },
                    elementAtPoint: atPoint ? atPoint.outerHTML : null
                };
                if (includeFocusState) {
                    details.visibilityState = document.visibilityState;
                    details.hidden = document.hidden;
                    details.navigatorWebdriver = navigator.webdriver;
                    details.activeElementOuterHTML = document.activeElement ? document.activeElement.outerHTML : null;
                    details.windowRect = {
                        innerWidth: window.innerWidth,
                        innerHeight: window.innerHeight,
                        outerWidth: window.outerWidth,
                        outerHeight: window.outerHeight
                    };
                    details.screen = {
                        width: window.screen.width,
                        height: window.screen.height
                    };
                }
                return details;
                '''
            details = cast(dict[str, Any], self._execute_javascript(script, element, self.debug_click_focus))
            log.warning('CLICK DEBUG %s %s', stage, details)
        except Exception as ex:
            log.warning('CLICK DEBUG %s failed: %s: %s', stage, ex.__class__.__name__, ex)

    def _log_post_click_state(self, stage: str) -> None:
        if not self.debug_clicks:
            return
        for delay in (0.0, 0.2, 1.0):
            if delay:
                sleep(delay)
            try:
                script = '''
                    const includeFocusState = arguments[0];
                    const details = {
                        url: window.location.href,
                        readyState: document.readyState,
                        hasFocus: document.hasFocus(),
                        activeTag: document.activeElement ? document.activeElement.tagName : null,
                        title: document.title
                    };
                    if (includeFocusState) {
                        details.visibilityState = document.visibilityState;
                        details.hidden = document.hidden;
                        details.navigatorWebdriver = navigator.webdriver;
                        details.activeElementOuterHTML = document.activeElement ? document.activeElement.outerHTML : null;
                        details.windowRect = {
                            innerWidth: window.innerWidth,
                            innerHeight: window.innerHeight,
                            outerWidth: window.outerWidth,
                            outerHeight: window.outerHeight
                        };
                        details.screen = {
                            width: window.screen.width,
                            height: window.screen.height
                        };
                    }
                    return details;
                    '''
                details = cast(dict[str, Any], self._execute_javascript(script, self.debug_click_focus))
                log.warning('CLICK DEBUG %s +%.1fs %s', stage, delay, details)
            except Exception as ex:
                log.warning('CLICK DEBUG %s +%.1fs failed: %s: %s',
                            stage, delay, ex.__class__.__name__, ex)


    def _force_kill_driver_tree(self) -> None:
        # noinspection PyBroadException
        try:
            svc = getattr(self, "service", None)
            proc = getattr(svc, "process", None) if svc else None
            pid = getattr(proc, "pid", None)
            if pid and os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        except Exception:
            log.exception("force-kill fallback failed")

    def _timeout(self, timeout: int | None = None) -> int:
        """
        Returns timeout value to be used

        :param timeout: timeout parameter passed to the function
        :return: timeout parameter value if not None, default timeout (options.timeout) otherwise
        """
        return timeout or self.options.timeout

    @staticmethod
    def dump_element(element: WebElement | None) -> str:
        """
        Dump web element data
        :param element: WebElement
        """
        if element is None:
            return ''
        try:
            retval = f'''Tag name: {element.tag_name}
Text content: {element.text}
Attributes:
'''
            attributes = cast(list[dict[str, Any]], cast(object, element.get_property('attributes')))
            for attribute in attributes:
                retval += f'  - {attribute["name"]} = {attribute["value"]}'
            retval += f'''Location on page: {element.location}
Size: {element.size}
'''
            return retval
        except Exception as ex:
            print(f'Exception occured while gathering detailed information for element {element}. '
                  f'Details:\n{ex.__class__.__name__}:{str(ex)}')
            return ''

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
                    return (elementAtPoint === element) || 
                    element.contains(elementAtPoint) || 
                    elementAtPoint.contains(element);
                } else {
                    return false;
                }
            '''
            if browser._execute_javascript(script, element):
                return element
            return False

        return _check
