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
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self.path = Path(self._base_dir, value)

    def delete(self) -> None:
        log.debug('Deleting profile directory: "%s"', self.path)
        if self.path and self.path.exists() and not self.persistent:
            for i in range(self.delete_retries):
                try:
                    shutil.rmtree(self.path)
                    return
                except PermissionError:
                    try:
                        sleep(self.delete_retries_interval * 2 ** i)
                    except OSError:
                        pass
            else:
                log.error('Could not delete profile directory "%s" in %s retries',
                          self.path, self.delete_retries)

    @classmethod
    def create_from(cls, other: 'Profile') -> 'Profile':
        return cls(
            other.name,
            other._base_dir,
            other.persistent,
            other.delete_retries,
            other.delete_retries_interval
        )

