"""
    User agent string management
"""
import random

class UserAgent:
    """
        Manage user agent strings
    """
    def __init__(self, platform: str) -> None:
        self.platform = platform.lower()
        # Map containing a per-OS lists of user agent string values
        self._strings = {
            'windows': [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/138.0.7204.49 Safari/537.36'
                # Edge
                'Mozilla/5.0 (Windows NT 10.0) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Edge/79.0.1451.30 '
                'Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0)'
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Edge/72.0.2685.132 '
                'Safari/537.36',
                # Firefox
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) '
                'Gecko/20100101 '
                'Firefox/146.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) '
                'Gecko/20100101 '
                'Firefox/138.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) '
                'Gecko/20100101 '
                'Firefox/136.0',
                # IE
                'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko',
                'Mozilla/5.0 (compatible; '
                'MSIE 10.6; Windows NT 6.1; Trident/5.0; InfoPath.2; '
                'SLCC1; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET CLR 2.0.50727) 3gpp-gba UNTRUSTED/1.0'
                # Opera
                'Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14',
                'Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.16.2',
            ],
            'linux': [
                'Mozilla/5.0 (X11; Linux x86_64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/138.0.7204.49 Safari/537.36'
                # Firefox
                'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0',
                'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0',
                'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0',
                # Konqueror
                'Mozilla/5.0 (X11; Linux) KHTML/4.9.1 (like Gecko) Konqueror/4.9',
                'Mozilla/5.0 (X11; Linux) KHTML/4.5.4 (like Gecko) Konqueror/4.5',
                # Opera
                'Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16.2',
                'Opera/12.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.10.289 Version/12.02'
            ]
        }
        self._current = self.default

    @property
    def random(self) -> str:
        """
        Returns a random user agent string
        """
        return random.choice(self._strings[self.platform])

    @property
    def default(self) -> str:
        """
        Returns a default value of a user agent string
        """
        return self._strings[self.platform][0]

    @property
    def current(self) -> str:
        """
        Returns the current value of a user agent string as set by next() and/or reset() methods
        """
        return self._current

    def next(self) -> None:
        """
        Selects next random user agent string as a current one
        """
        self._current = self.random

    def reset(self) -> None:
        """
        Resets the current value of a user agent string to the default one
        :return:
        """
        self._current = self.default