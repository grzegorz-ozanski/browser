"""
    Automatically download the latest stable Chrome driver and Chrome
"""
import io
import os
import shutil
import zipfile
from enum import StrEnum
from pathlib import Path
from typing import Any

import requests
from .log import setup_logging
from functools import cached_property
log = setup_logging(__name__)

CHROME_API_ENDPOINT_URL = \
    'https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json'


def unpack(content: bytes, archive_dir: str, output_dir: str | Path) -> None:
    """
    Unpack downloaded zip archive replacing internal root dir with provided one

    :param content: compressed ZIP content
    :param archive_dir: archive directory to be replaced with :param output_dir
    :param output_dir: value to replace the :param archive_dir with when unpacking the archive
    """
    with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
        for info in zip_file.infolist():
            if info.filename.startswith(archive_dir + "/") and not info.filename.endswith("/"):
                # Replace archive_dir prefix with target_dir one
                relative_path = info.filename[len(archive_dir) + 1:]
                target_path = Path(output_dir, relative_path)
                os.makedirs(target_path.parent, exist_ok=True)
                with zip_file.open(info) as src, open(target_path, "wb") as dst:
                    # supress the warning as the result of open() actually is a BufferedWriter
                    # noinspection PyTypeChecker
                    shutil.copyfileobj(src, dst)
                mode = info.external_attr >> 16
                if mode:
                    os.chmod(target_path, mode)

class ChromeDownloader:
    """
        Download and unpack the latest stable Chrome driver and Chrome
    """

    class Component(StrEnum):
        """
        Component name
        """
        CHROME = 'chrome'
        CHROMEDRIVER = 'chromedriver'

    def __init__(self, platform_name: str) -> None:
        """
            Initialize the downloader with platform-specific settings.
        """
        self.platform_name = platform_name

    @cached_property
    def downloads(self) -> Any:
        """
        Latest available stable downloads

        :return: Dictionary containing downloads info
        """
        response = requests.get(CHROME_API_ENDPOINT_URL)
        response.raise_for_status()
        data = response.json()
        return data['channels']['Stable']['downloads']

    def download_all(self, chromedriver_root: Path, chrome_subdir: str | Path) -> None:
        """
        Downloads all components (Chrome driver and Chrome) into directories provided. Target directory tree will be:

        <chromedriver_root>/
            ├── chromedriver[.exe]
            └── <chrome_subdir>/
                ├── [chrome files]
                └── chrome[.exe]

        :param chromedriver_root: root directory where Chromedriver will be placed
        :param chrome_subdir: subdirectory inside :param chromedriver_root where Chrome files will be placed
        """
        self.download(ChromeDownloader.Component.CHROMEDRIVER, chromedriver_root)
        self.download(ChromeDownloader.Component.CHROME, chromedriver_root / chrome_subdir)

    def download(self, what: Component, where: str | Path) -> None:
        """
        Download single component
        :param what: component name
        :param where: destination directory
        """
        url = next(item for item in self.downloads[what] if item['platform'] == self.platform_name)['url']
        log.debug(f'Downloading {what} from {url}')
        response = requests.get(url)
        response.raise_for_status()
        archive_dir = f'{what}-{self.platform_name}'

        unpack(response.content, archive_dir, where)
