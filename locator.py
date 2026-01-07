"""
    Web page element locator module
"""
from dataclasses import dataclass

@dataclass
class Locator:
    """Element locator used for finding inputs and buttons in the page."""
    type: str
    value: str

    def __repr__(self) -> str:
        """String representation of the locator."""
        return f'[({self.type}) {self.value}]'