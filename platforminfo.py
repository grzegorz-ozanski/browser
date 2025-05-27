"""
    Platform info module for easier interaction with Google Chrome driver/Chrome downloads
"""
import platform
import sys

class PlatformInfo:
    """
    Store both user-friendly system name and platform string compatible with Google Chrome/Chromedriver
    downloads API JSON
    """
    unknown = '<unknown>'
    def __init__(self) -> None:
        """
            Initialize platform detection info for browser configuration.
        """
        self.system = platform.system()
        machine = platform.machine().lower()

        if self.system == 'Linux':
            self.platform =  'linux64'
        elif self.system == 'Darwin':
            self.platform = 'mac-arm64' if 'arm' in machine else 'mac-x64'
        elif self.system == 'Windows':
            self.platform = 'win64' if sys.maxsize > 2 ** 32 else 'win32'
        else:
            self.platform = self.unknown

    def system_is(self, *name: str) -> bool:
        """
        Check if system is any of the ones provided in name
        :param name: list of systems to check
        :return: True if system matches any provided names, False otherwise
        """
        return self.system in name