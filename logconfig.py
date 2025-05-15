import os
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from str_to_bool import str_to_bool

T = TypeVar('T', bound=Any)


@dataclass
class EnvironmentValue(Generic[T]):
    """
    Cached environment value
    """
    env_key: str
    default: T
    _value: T | None = None
    _value_type: type = field(init=False)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __setattr__(self, key: str, value: object) -> None:
        if key == 'default':
            self._value_type = type(value)
        elif key == '_value' and self._value_type is bool and value is not None:
            value = bool(str_to_bool(str(value)))
        super().__setattr__(key, value)

    @property
    def value(self) -> T:
        """
        Get logger configuration item value

        :return: item value
        """
        if self._value is None:
            self._value = os.environ.get(self.env_key, self.default)
        return self._value

@dataclass
class LogConfig:
    """
    Logger configuration
    """
    level: EnvironmentValue[str] = field(
        default_factory=lambda: EnvironmentValue('BROWSER_LOG_LEVEL', 'DEBUG'))
    formatting: EnvironmentValue[str] = field(
        default_factory=lambda: EnvironmentValue('BROWSER_LOG_FORMATTING',
                                                 '%(levelname)s:%(name)s %(asctime)s %(message)s'))
    console: EnvironmentValue[bool] = field(
        default_factory=lambda: EnvironmentValue('BROWSER_LOG_TO_CONSOLE', True))
    file: EnvironmentValue[str] = field(
        default_factory=lambda: EnvironmentValue('BROWSER_LOG_FILENAME', ''))
    initialized: bool = False


LOG_CONFIG = LogConfig()
