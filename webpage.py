from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from log import setup_logging

log = setup_logging(__name__, 'DEBUG')


def _browser_options(options):
    driver_options = Options()
    for opt in options:
        driver_options.add_argument(opt)
    return driver_options


class WebPage:
    def wait_for_elements(self, value, by=By.CLASS_NAME, delay=None):
        items = None
        delay = self._default_delay if delay is None else delay
        try:
            items = WebDriverWait(self, delay).until(
                EC.presence_of_all_elements_located((by, value)))
        except TimeoutException:
            pass
        return items

    def wait_for_ajax(self, delay=None):
        delay = self._default_delay if delay is None else delay
        wait = WebDriverWait(self, delay)
        try:
            wait.until(lambda driver: driver.execute_script('return jQuery.active') == 0)
            wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
        except Exception as e:
            pass
        return True


class Remote(webdriver.Remote, WebPage):
    def __init__(self, url, options, default_delay):
        self._default_delay = default_delay
        super().__init__(url, options=_browser_options(options))
        log.debug("%s object initialised" % __class__)


class Chrome(webdriver.Chrome, WebPage):
    def __init__(self, path, options, default_delay):
        self._default_delay = default_delay
        super().__init__(path, options=_browser_options(options))
        log.debug("%s object initialised" % __class__)
