"""
    Browser options
"""
import re
import subprocess
import tempfile
from pathlib import Path

from .chromedownloader import ChromeDownloader
from .platforminfo import PlatformInfo


def get_chrome_version(chrome_path: str, platform: str) -> str:
    """
    Gets Chrome version used
    :param chrome_path: Path to the chrome binary
    :param platform: 'Linux' or 'Windows'
    :return: Chrome version string
    """
    try:
        if platform == 'Linux':
            output = subprocess.check_output([chrome_path, '--version'], stderr=subprocess.STDOUT)
            # example output: "Google Chrome 138.0.7204.49"
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)', output.decode())
            if match:
                return match.group(1)
        else:
            output = subprocess.check_output(['powershell', '-command',f"(Get-Item '{chrome_path}').VersionInfo.ProductVersion"], stderr=subprocess.STDOUT)
            return output.decode().strip()
    except Exception as e:
        print(f"[WARN] Could not detect Chrome version: {e}")
    # fallback
    return "113.0.0.0"


class BrowserOptions:
    """
    Browser options class
    """

    def __init__(self, root_path: str, headless: bool, save_trace_logs: bool, timeout: int = 10) -> None:
        """
        Class construstor
        :param root_path: Chromediver root path
        :param headless: run Chrome browser in headless mode
        :param save_trace_logs: if 'True', trace logs on page elements operations are saved
        :param timeout: default timeout value for relevant operations
        """
        self.chromedriver_location = ''
        self.chrome_location = ''
        self.user_data_dir = None
        self.driver_options = ['window-size=1200,1100', 'log-level=3', 'disable-dev-shm-usage']
        self.save_trace_logs = save_trace_logs
        if headless:
            self.driver_options.append('headless')
        self.timeout = timeout
        version = self._configure_chromedriver_location(root_path)
        self.driver_options.append('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                   f'(KHTML, like Gecko) Chrome/{version} Safari/537.36') # for multimedia service login error in headless mode
        # Options that potentially lowers reCaptcha v3 (automatic bot detection) score, making some page unusable
        self.driver_options += ['disable-gpu', 'disable-webgl', 'enable-unsafe-swiftshader', 'no-sandbox']
        # Another remedy for reCatcha v3
        self.user_data_dir = Path(tempfile.gettempdir(), "myprofile")
        self.driver_options += [f'user-data-dir={self.user_data_dir}']
        self.error_log_dir = 'error'

    def __repr__(self) -> str:
        """
            Return string representation of the object.
        """
        return ', '.join([f'{name}={value}' for name, value in self.__dict__.items()])

    def _configure_chromedriver_location(self, root_path: str) -> str:
        """
        Configure a Chrome/Chromedriver path per operating system. Expectedy folder layout:
        root_path/
            └── chromedriver/
                ├── chromedriver[.exe]
                └── chrome/
                    ├── <chrome files>
                    └── chrome[.exe]
        :param root_path: Chrome/Chromedriver root path
        :returns Version of Chrome/Chromedriver connfigured
        """
        platform_info = PlatformInfo()
        if platform_info.system_is('Darwin'):  # running on macOS
            self.chromedriver_location = '/Users/greggor/Downloads/chromedriver'
            return '' #TODO fix
        if platform_info.system_is('Linux', 'Windows'):
            chromedriver_root = Path(root_path).parent.joinpath('chromedriver')
            if not chromedriver_root.exists():
                print(f'Chromedriver not found in "{chromedriver_root}", downloading...')
                chrome_downloader = ChromeDownloader(platform_info.platform)
                chrome_downloader.download_all(chromedriver_root, 'chrome')
            chromedriver_root = chromedriver_root.resolve(True)
            self.chromedriver_location = str(chromedriver_root.joinpath('chromedriver'))
            self.chrome_location = str(chromedriver_root.joinpath('chrome').joinpath('chrome'))
            if platform_info.system_is('Windows'):
                self.chromedriver_location += '.exe'
                self.chrome_location += '.exe'
                return get_chrome_version(self.chrome_location, 'Windows')
            return get_chrome_version(self.chrome_location, 'Linux')
        else:
            raise NotImplementedError(f'"{platform_info.system}" is not supported.')
