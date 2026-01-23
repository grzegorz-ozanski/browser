"""
    User profile module
"""
import shutil
from pathlib import Path
from time import sleep
from .log import setup_logging

log = setup_logging(__name__)



class Profile:
    """
    Stores information about user profile directory
    """

    def __init__(self, name: str, base_dir: str, persistent: bool, delete_retries: int = 3, delete_retries_interval: int = 5):
        self._name = name
        self._base_dir = base_dir
        self.path = Path(base_dir, name)
        self.persistent = persistent
        self.delete_retries = delete_retries
        self.delete_retries_interval = delete_retries_interval

    def __repr__(self) -> str:
        return f'Profile (name={self.name}, path="{self.path}")'

    @property
    def name(self) -> str:
        """
        Return profile name
        :return: The name of the profile
        """
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self.path = Path(self._base_dir, value)

    def delete_not_persistent(self) -> None:
        """
        Delete volatile profile directory
        """
        if self.persistent:
            log.debug('Refusing to delete persistent profile directory "%s"', self.path)
            return
        if self.path and self.path.exists():
            log.debug('Deleting volatile profile directory: "%s"', self.path)
            for i in range(self.delete_retries):
                try:
                    shutil.rmtree(self.path)
                    return
                except PermissionError:
                    sleep_time = self.delete_retries_interval * 2 ** i
                    log.warning('PermissionError occurred while deleting profile directory "%s" at %s attempt,'
                                'sleeping %s seconds', self.path, i, sleep_time)
                    try:
                        sleep(self.delete_retries_interval * 2 ** i)
                    except OSError:
                        pass
            else:
                message = (f'Could not delete volatile profile directory "self.path" in self.delete_retries retries.'
                           'Fresh profile cannot be created, aborting')
                log.error(message)
                raise RuntimeError(message)

    @classmethod
    def create_from(cls, other: 'Profile') -> 'Profile':
        """
        Copy constructor
        :param other: template object
        :return: new profile object created from template provided
        """
        return cls(
            other.name,
            other._base_dir,
            other.persistent,
            other.delete_retries,
            other.delete_retries_interval
        )

