from dataclasses import dataclass

@dataclass
class PageElement:
    """Element locator used for finding inputs and buttons in the page."""
    by: str
    selector: str

    def __repr__(self):
        return f'({self.by}) {self.selector}'