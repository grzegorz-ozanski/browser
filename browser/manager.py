"""
    Browser manager module
"""
from contextlib import contextmanager
from os import getenv
from typing import Any, Generator

from .browser import Browser
from .log import setup_logging
from .options import BrowserOptions, PROFILE_NAME
from .profile import Profile

log = setup_logging(__name__)


class BrowserManager:
    """
    Browser manager class for handling switchitng between persistent and volatile profiles
    """
    def __init__(self, options: BrowserOptions, factory: type[Browser]):
        self.options = options
        self.persistent_profile = options.profile
        self.volatile_profile: Profile | None = None
        self.browser: Browser | None = None
        self.factory = factory
        self.debug_profile = getenv('BROWSER_DEBUG_PROFILE', '0') == '1'

    # noinspection PyBroadException
    @contextmanager
    def session(self, recaptcha_v3: bool) -> Generator[Browser, Any, None]:
        """
        Context manager for getting browser instance with either persistent profile or volatile user profile
        :param recaptcha_v3: avoid reCAPTCHA v3 detection by using volatile user profile

        :return: Browser instance
        """
        browser = self._get(recaptcha_v3)
        try:
            yield browser
        finally:
            # Delete volatile profile
            if recaptcha_v3:
                log.debug("Ending volatile session -> quitting browser")
                try:
                    browser.quit()
                except Exception:
                    log.exception("browser.quit() failed")
                self.browser = None
                # We need nested ifs here as self.volatile_profile variable itself is persistent
                if self.volatile_profile:
                    try:
                        self.volatile_profile.delete_not_persistent()
                    except Exception:
                        log.exception("volatile profile cleanup failed")

    def _get(self, recaptcha_v3: bool) -> Browser:
        """
        Get browser instance with either persistent profile or volatile user profile
        :param recaptcha_v3: avoid reCAPTCHA v3 detection by using volatile user profile

        :return: Browser instance
        """
        if not recaptcha_v3 and self.browser and self.browser.options.profile.persistent:
            # Always create a new browser when volatile profile is requested.
            # So, return exting instance only if:
            # 1. use_volatile_profile=False,
            # 2. we already have a browser instance
            # 3. the browser instance uses persistent profile
            log.debug('Using existing browser instance')
            return self.browser

        if self.browser:
            log.debug('Deleting existing browser instance')
            self.browser.quit()
            if self.volatile_profile:
                self.volatile_profile.delete_not_persistent()
            self.browser = None

        if recaptcha_v3:
            log.debug('Creating new volatile profile browser instance')
            if not self.volatile_profile:
                self.volatile_profile = Profile.create_from(self.persistent_profile)
                self.volatile_profile.name = f'{PROFILE_NAME}.volatile'
                self.volatile_profile.persistent = False
                # Force creation of fresh volatile profile directory
                self.volatile_profile.delete_not_persistent()
            self.options.profile = self.volatile_profile
            self.options.user_agent.next()
            log.debug('User agent set to "%s"', self.options.user_agent.current)
        else:
            log.debug('Creating new persistent profile browser instance')
            self.options.profile = self.persistent_profile
            self.options.user_agent.reset()
            log.debug('User agent reset to default "%s"', self.options.user_agent.current)
        log.debug('Creating browser with profile in "%s"', self.options.profile.path)
        if self.debug_profile:
            input('Press ENTER to continue...')
        self.browser = self.factory(self.options)
        self.browser.set_page_load_timeout(self.options.renderer_timeout)
        self.browser.set_script_timeout(self.options.renderer_timeout)
        log.debug('Browser timezone is: %s, renderer timeout is: %d',
                  self.browser.timezone,
                  self.options.renderer_timeout)
        return self.browser

    def close(self) -> None:
        """
        Close Chrome browser instance
        """
        if self.browser:
            # noinspection PyBroadException
            try:
                self.browser.quit()
            except Exception:
                log.exception("browser.quit() failed in BrowserManager.close()")
            finally:
                self.browser = None

        if self.volatile_profile:
            # noinspection PyBroadException
            try:
                self.volatile_profile.delete_not_persistent()
            except Exception:
                log.exception("volatile profile cleanup failed in BrowserManager.close()")
