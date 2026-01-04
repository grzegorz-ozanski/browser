"""
    Browser options
"""
import tempfile
from pathlib import Path

from .chromedownloader import ChromeDownloader
from .platforminfo import PlatformInfo
from .profile import Profile

PROFILE_NAME = 'myprofile'

class BrowserOptions:
    SEP = ', '
    """
    Browser options class
    """

    def __init__(self,
                 root_path: str,
                 headless: bool,
                 save_trace_logs: bool,
                 chrome_path: str,
                 persistent_profile: bool = False,
                 profile_name: str = PROFILE_NAME,
                 timeout: int = 10) -> None:
        """
        Class construstor
        :param root_path: Chromediver root path
        :param headless: run Chrome browser in headless mode
        :param save_trace_logs: if 'True', trace logs on page elements operations are saved
        :param chrome_path: Chrome path override
        :param timeout: default timeout value for relevant operations
        """
        self.chromedriver_location = ''
        self.chrome_location = ''
        self._driver_options = ['disable-blink-features=AutomationControlled', 'window-size=1920,1200', 'log-level=3', 'disable-dev-shm-usage']
        self.save_trace_logs = save_trace_logs
        if headless:
            self._driver_options.append('headless')
        self.timeout = timeout
        self._configure_chromedriver_location(root_path, chrome_path)
        self._driver_options.append('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                   f'(KHTML, like Gecko) Chrome/138.0.7204.49 Safari/537.36') # for multimedia service login error in headless mode
        # Options that potentially lowers reCaptcha v3 (automatic bot detection) score, making some page unusable
        self._driver_options += ['disable-gpu', 'disable-webgl', 'enable-unsafe-swiftshader', 'no-sandbox']
        # Another remedy for reCatcha v3
        self.profile = Profile(profile_name, tempfile.gettempdir(), persistent_profile)
        self.error_log_dir = 'error'

    @property
    def driver_options(self) -> list[str]:
        options = self._driver_options
        return options + [f'user-data-dir={self.profile.path}']

    def __repr__(self) -> str:
        """
            Return string representation of the object.
        """
        return self.SEP.join([f'{name}={value}' for name, value in self.__dict__.items()])

    def _configure_chromedriver_location(self, root_path: str, chrome_path: str) -> None:
        """
        Configure a Chrome/Chromedriver path per operating system. Expectedy folder layout:
        root_path/
            └── chromedriver/
                ├── chromedriver[.exe]
                └── chrome/
                    ├── <chrome files>
                    └── chrome[.exe]
        :param root_path: Chrome/Chromedriver root path
        :param chrome_path: Chrome path override
        """
        platform_info = PlatformInfo()
        if platform_info.system_is('Darwin'):  # running on macOS
            self.chromedriver_location = '/Users/greggor/Downloads/chromedriver'
        if platform_info.system_is('Linux', 'Windows'):
            chromedriver_root = Path(root_path).parent.joinpath('chromedriver')
            if not chromedriver_root.exists():
                print(f'Chromedriver not found in "{chromedriver_root}", downloading...')
                chrome_downloader = ChromeDownloader(platform_info.platform)
                chrome_downloader.download_all(chromedriver_root, 'chrome')
            chromedriver_root = chromedriver_root.resolve(True)
            self.chromedriver_location = str(chromedriver_root.joinpath('chromedriver'))
            if not chrome_path:
                self.chrome_location = str(chromedriver_root.joinpath('chrome').joinpath('chrome'))
            else:
                self.chrome_location = chrome_path
            if platform_info.system_is('Windows'):
                self.chromedriver_location += '.exe'
                if not chrome_path:
                    # Append '.exe' extension to Chrome path only if it was autodetected
                    self.chrome_location += '.exe'
        else:
            raise NotImplementedError(f'"{platform_info.system}" is not supported.')

    def as_log_str(self) -> str:
        return '\n' + str(self).replace(self.SEP,f'{self.SEP}\n')