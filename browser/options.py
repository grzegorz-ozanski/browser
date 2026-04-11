"""
    Browser options
"""
import tempfile
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from pathlib import Path

from .chromedownloader import ChromeDownloader
from .platforminfo import PlatformInfo
from .profile import Profile
from .useragent import UserAgent

PROFILE_NAME = 'myprofile'


class BrowserOptions:
    """
    Browser options class
    """
    SEP = ', '

    def __init__(self,
                 headless: bool = False,
                 save_trace_logs: bool = False,
                 profile_dir: str = '',
                 persistent_profile: bool = False,
                 profile_name: str = PROFILE_NAME,
                 chromedriver_path: str  = '',
                 chrome_path: str  = '',
                 timeout: int = 10,
                 renderer_timeout: int = 10) -> None:
        """
        Class construstor
        :param chromedriver_path: Chromediver root path
        :param headless: run Chrome browser in headless mode
        :param save_trace_logs: if 'True', trace logs on page elements operations are saved
        :param chrome_path: Chrome path override
        :param timeout: default timeout value for relevant operations
        """
        self.chromedriver_location = ''
        self.chrome_location = ''
        self._driver_options = ['disable-blink-features=AutomationControlled',
                                'window-size=1920,1200',
                                'log-level=3',
                                'disable-dev-shm-usage',
                                'remote-debugging-pipe']
        self.platform_info = PlatformInfo()
        if self.platform_info.system == 'Linux':
            # Without it: Chrome for Testing crashes in Linux Docker GitHub Runner environment
            # With it: Multimedia provider cannot log in on Windows
            self._driver_options.append('no-sandbox')
        self.headless = headless
        if self.headless:
            self._driver_options.append('headless')
        self.user_agent = UserAgent(self.platform_info.system)
        self.save_trace_logs = save_trace_logs
        self.timeout = timeout
        self.renderer_timeout = renderer_timeout
        self._configure_chromedriver_location(chromedriver_path, chrome_path)
        # Another remedy for reCatcha v3
        self.profile = Profile(profile_name, profile_dir or tempfile.gettempdir(), persistent_profile)
        self.error_log_dir = 'error'

    @property
    def driver_options(self) -> list[str]:
        """
        Returns driver options list
        :return: driver options list
        """
        options = self._driver_options
        return options + [f'user-data-dir={self.profile.path}', f'user-agent={self.user_agent.current}']

    def __repr__(self) -> str:
        """
            Return string representation of the object.
        """
        return self.SEP.join([f'{name}={value}' for name, value in self.__dict__.items()])

    def _configure_chromedriver_location(self, chromedriver_path: str, chrome_path: str ) -> None:
        """
        Configure a Chrome/Chromedriver path per operating system. Expectedy folder layout:
        root_path/
            └── chromedriver/
                ├── chromedriver[.exe]
                └── chrome/
                    ├── <chrome files>
                    └── chrome[.exe]
        :param chromedriver_path: Chrome/Chromedriver root path
        :param chrome_path: Chrome path override
        """
        if self.platform_info.system_is('Darwin'):  # running on macOS
            self.chromedriver_location = '/Users/greggor/Downloads/chromedriver'
        if self.platform_info.system_is('Linux', 'Windows'):
            chromedriver_root = Path(chromedriver_path) / 'chromedriver'
            if not chromedriver_root.exists():
                print(f'Chromedriver not found in "{chromedriver_root}", downloading...')
                chrome_downloader = ChromeDownloader(self.platform_info.platform)
                chrome_downloader.download_all(chromedriver_root, 'chrome')
            chromedriver_root = chromedriver_root.resolve(True)
            self.chromedriver_location = str(chromedriver_root.joinpath('chromedriver'))
            if not chrome_path:
                self.chrome_location = str(chromedriver_root.joinpath('chrome').joinpath('chrome'))
            else:
                self.chrome_location = chrome_path
            if self.platform_info.system_is('Windows'):
                self.chromedriver_location += '.exe'
                if not chrome_path:
                    # Append '.exe' extension to Chrome path only if it was autodetected
                    self.chrome_location += '.exe'
            chrome_version = self._chrome_version()
            if chrome_version:
                self.user_agent.chrome_version = chrome_version
        else:
            raise NotImplementedError(f'"{self.platform_info.system}" is not supported.')

    def _chrome_version(self) -> str:
        chrome_dir = Path(self.chrome_location).parent
        manifest = chrome_dir.glob('*.manifest')
        try:
            root = ET.parse(list(manifest)[0]).getroot()
            return root[0].attrib['version']
        except (IndexError, OSError, KeyError):
            return ''

    def as_log_str(self) -> str:
        """
        Return string representation of the object applicable for logging (each field in a new line).
        :return:
        """
        return '\n' + str(self).replace(self.SEP, f'{self.SEP}\n')
