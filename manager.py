"""
    Browser manager module
"""
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
        self.persistent_profile  = options.profile
        self.volatile_profile = None
        self.browser = None
        self.factory= factory

    def get(self, use_volatile_profile: bool) -> Browser:
        """
        Get browser instance with either persistent profile or volatile user profile
        :param use_volatile_profile: use volatile user profile

        :return: Browser instance
        """
        if not use_volatile_profile and self.browser and self.browser.options.profile.persistent:
            # Always create a new browser when volatile profile is requested.
            # So, return exting instance only if:
            # 1. use_volatile_profile=False,
            # 2. we already have a browser instance
            # 3. the browser instance uses persistent profile
            log.debug('Returning existing browser instance')
            return self.browser

        if self.browser:
            log.debug('Deleting existing browser instance')
            self.browser.quit()
            if self.volatile_profile:
                self.volatile_profile.delete_if_volatile()
            self.browser = None

        if use_volatile_profile:
            log.debug('Creating new volatile profile browser instance')
            if not self.volatile_profile:
                self.volatile_profile = Profile.create_from(self.persistent_profile)
                self.volatile_profile.name = f'{PROFILE_NAME}.volatile'
                self.volatile_profile.persistent = False
            else:
                # Force creation of fresh volatile profile directory
                self.volatile_profile.delete_if_volatile()
            self.options.profile = self.volatile_profile
        else:
            log.debug('Creating new persistent profile browser instance')
            self.options.profile = self.persistent_profile
        self.browser = self.factory(self.options)
        return self.browser

