"""
    Platform info module
"""
import platform
import sys

class PlatformInfo:
    """
    Store information about current system and platform
    """
    def __init__(self) -> None:
        self.system = platform.system()
        machine = platform.machine().lower()

        if self.system == 'Linux':
            self.platform =  'linux64'
        elif self.system == 'Darwin':
            self.platform = 'mac-arm64' if 'arm' in machine else 'mac-x64'
        elif self.system == 'Windows':
            self.platform = 'win64' if sys.maxsize > 2 ** 32 else 'win32'
        else:
            self.platform = '<unknown>'

    def system_is(self, *name: str) -> bool:
        """
        Check if system is any of the ones provided in name
        :param name: list of systems to check
        :return: True if system matches any provided names, False otherwise
        """
        return self.system in name