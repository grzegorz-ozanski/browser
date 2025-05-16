"""
    Browser options
"""
from pathlib import Path
from chromedownloader import ChromeDownloader

class BrowserOptions:
    """
    Browser options class
    """

    def __init__(self, root_path: str, system: str, headless: bool, save_trace_logs: bool, timeout: int = 10) -> None:
        """
        Class construstor
        :param root_path: Chromediver root path
        :param system: OS name
        :param headless: run Chrome browser in headless mode
        :param save_trace_logs: if 'True', trace logs on page elements operations will be saved
        :param timeout: default timeout value for relevant operations
        """
        self.exe_path = ''
        self.binary_location = ''
        self.driver_options = ["disable-gpu", "disable-webgl", "window-size=1200,1100", "log-level=3",
                               "no-sandbox", "disable-dev-shm-usage", "enable-unsafe-swiftshader",
                               # for multimedia service login error in headless mode
                               'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                               '(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36']
        self.save_trace_logs = save_trace_logs
        if headless:
            self.driver_options.append("headless")
        self.timeout = timeout
        self._configure_chromedriver_location(system, root_path)

    def _configure_chromedriver_location(self, platform: str, root_path: str) -> None:
        """
        Configure Chrome/Chromedriver path per operating system. Expectedy folder layout:
        root_path/
            └── chromedriver/
                ├── chromedriver[.exe]
                └── chrome/
                    ├── <chrome files>
                    └── chrome[.exe]
        :param platform: OS platform
        :param root_path: Chrome/Chromedriver root path
        """
        if 'mac' in platform:  # running on macOS
            self.exe_path = "/Users/greggor/Downloads/chromedriver"
        elif 'win' in platform or 'linux' in platform:
            chromedriver_root = Path(root_path).parent.joinpath('chromedriver')
            if not chromedriver_root.exists():
                print(f'Chromedriver not found in "{chromedriver_root}", downloading...')
                chrome_downloader = ChromeDownloader(platform)
                chrome_downloader.download_all(chromedriver_root, 'chrome')
            chromedriver_root = chromedriver_root.resolve(True)
            self.exe_path = f"{chromedriver_root.joinpath('chromedriver')}"
            self.binary_location = str(chromedriver_root.joinpath("chrome").joinpath("chrome"))
            if platform == 'Windows':
                self.exe_path += ".exe"
                self.binary_location += ".exe"
        else:
            raise NotImplementedError(f"'{platform}' is not supported.")
