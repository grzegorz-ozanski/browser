from webpage import Remote, Chrome
from log import setup_logging

log = setup_logging(__name__, 'DEBUG')


class Browser:
    instance = None

    def __init__(self, url="http://127.0.0.1:9515", delay=10, options=[]):
        if Browser.instance is None:
            protocol = url.split("://")

            if protocol[0] == "http":
                log.debug("Creating new Browser instance with parameters: driver_url=%s, delay=%d, options=%s"
                          % (url, delay, options))
                Browser.instance = Remote(url, options, delay)
            elif protocol[0] == "file":
                log.debug("Creating new Browser instance with parameters: <Chrome>, delay=%d, options=%s"
                          % (delay, options))
                Browser.instance = Chrome(protocol[1], options, delay)
            else:
                raise Exception("Unknown protocol: %s" % protocol[0])
        else:
            log.debug("Using stored Browser instance")

    @staticmethod
    def delete():
        if Browser.instance is not None:
            log.debug("Deleting Browser instance")
            Browser.instance.close()
        else:
            log.debug("Browser instance does not exist, nothing to do")

