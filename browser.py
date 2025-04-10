from log import setup_logging
from time import sleep
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Remote, Chrome
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

    def wait_for_page_load_completed(self):
        state = None
        while state != "complete":
            state = self.browser.execute_script('return document.readyState')
            log.debug(state)
            sleep(0.1)

    def wait_for_page_inactive(self, timeout=30):
        script = """
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
                }, """ + str(timeout * 1000) + """);
            });
        """
        return self.browser.execute_script(script)

    def wait_for_network_inactive(self, timeout=30):
        # Additional check for network activity
        network_idle_script = """
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
                setTimeout(() => resolve(false), """ + str((timeout - 4) * 1000) + """);
            });
        """
        self.browser.execute_script(network_idle_script)

        # Finally, wait a short time for any final rendering or initialization
        sleep(0.5)

    def wait_for_element_inactive(self, selector, timeout=10):
        """Wait for an element to stop changing position and size.
        :param selector: CSS selector. Valid examples:
                            ID selector: "#main-content"
                            Class selector: ".product-card"
                            Element type selector: "button"
                            Attribute selector: "[data-test-id='submit-button']"
                            Descendant selector: ".container .item"
                            Complex selector: "div.results > ul > li:nth-child(3)"
                            Multiple selectors: "header nav, .sidebar, #footer"
        :param timeout:
        :return:
        """
        script = """
            const selector = arguments[0];
            return new Promise(resolve => {
                const element = document.querySelector(selector);
                if (!element) {
                    resolve(false);
                    return;
                }

                let lastRect = element.getBoundingClientRect();
                const checkStability = () => {
                    const currentRect = element.getBoundingClientRect();
                    if (currentRect.top === lastRect.top && 
                        currentRect.left === lastRect.left &&
                        currentRect.width === lastRect.width &&
                        currentRect.height === lastRect.height) {
                        resolve(true);
                    } else {
                        lastRect = currentRect;
                        setTimeout(checkStability, 100);
                    }
                };

                setTimeout(checkStability, 100);
                setTimeout(() => resolve(false), """ + str(timeout * 1000) + """);
            });
        """
        return self.browser.execute_script(script, selector)

    def wait_for_elements(self, by, value, delay=None):
        items = None
        delay = self._default_delay if delay is None else delay
        try:
            items = WebDriverWait(self, delay).until(
                EC.visibility_of_all_elements_located((by, value)))
        except TimeoutException:
            pass
        return items

    def wait_for_element(self, by, value, delay=None):
        items = self.wait_for_elements(by, value, delay)
        return items[0] if items is not None else None

    def wait_for_element_ex(self, by, value, delay=None, retries=3):
        items = None
        while items is None and retries > 0:
            items = self.wait_for_elements(by, value, delay)
            retries -= 1
        return items[0] if items is not None else None

    def find_element_ex(self, by, value, query=None):
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

    def click_element(self, by, value):
        element = self.browser.find_element(by, value)
        self.browser.execute_script("arguments[0].click()", element)


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
