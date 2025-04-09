from log import setup_logging
from time import sleep
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Remote, Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
import re

log = setup_logging(__name__, 'DEBUG')


def _browser_options(options):
    driver_options = Options()
    for opt in options:
        driver_options.add_argument(opt)
    return driver_options

def _browser_factory(webdriver_class, url, options, binary_location):
    if options is None:
        options = []
    driver_options = _browser_options(options)
    if binary_location:
        driver_options.binary_location = binary_location
    return webdriver_class(url, options=driver_options)

# noinspection PyMissingConstructor
class BrowserBase(WebDriver):
    def __init__(self, delay):
        self.browser = None
        self._default_delay = delay

    def wait_for_load(self):
        state = None
        while state != "complete":
            state = self.browser.execute_script('return document.readyState')
            log.debug(state)
            sleep(0.1)

    def wait_for_elements(self, value, by=By.CLASS_NAME, delay=None):
        items = None
        delay = self._default_delay if delay is None else delay
        try:
            items = WebDriverWait(self, delay).until(
                EC.visibility_of_all_elements_located((by, value)))
        except TimeoutException:
            pass
        return items

    def wait_for_element(self, value, by=By.CLASS_NAME, delay=None):
        items = self.wait_for_elements(value, by, delay)
        return items[0] if items is not None else None

    def wait_for_element_ex(self, value, by=By.CLASS_NAME, delay=None, retries=3):
        items = None
        while items is None and retries > 0:
            items = self.wait_for_elements(value, by, delay)
            retries -= 1
        return items[0] if items is not None else None

    def find_element_ex(self, by=By.ID, value=None, query=None):
        items = self.browser.find_elements(by, value)
        ops = {'=': lambda x, y: x == y,
               '!=': lambda x, y: x != y
               }
        operators = ''.join(set([i for items in ops.keys() for i in items]))
        m = re.match(f"([^{operators}]+?)\\s*([{operators}]+)\\s*([^{operators}]+)", query)
        property_name = m[1]
        property_value = None
        expected_value = m[3]
        property_operator = m[2]
        for item in items:
            try:
                property_value = getattr(item, property_name)
            except AttributeError:
                try:
                    property_value = item.get_attribute(property_name)
                except AttributeError:
                    pass
            if ops[property_operator](property_value, expected_value):
                return item
        return None


class Browser(BrowserBase):

    def __init__(self, url="http://127.0.0.1:9515", delay=10, options=None, binary_location=''):
        super().__init__(delay)
        protocol = url.split("://")

        if protocol[0] == "http":
            log.debug("Creating new Browser instance with parameters: driver_url=%s, delay=%d, options=%s"
                      % (url, delay, options))
            self.browser = _browser_factory(Remote, url, options, binary_location)
        elif protocol[0] == "file":
            log.debug("Creating new Browser instance with parameters: <Chrome>, delay=%d, options=%s"
                      % (delay, options))
            self.browser = _browser_factory(Chrome, protocol[1], options, binary_location)
        else:
            raise Exception("Unknown protocol: %s" % protocol[0])

    def __getattribute__(self, item):
        try:
            return super().__getattribute__(item)
        except AttributeError:
            return self.browser.__getattribute__(item)
