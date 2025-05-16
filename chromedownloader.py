"""
    Automatically download latest stable Chrome driver and Chrome
"""
import io
import os
import shutil
import zipfile
from enum import StrEnum
from pathlib import Path
from typing import Any

import requests

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
        for member in zip_file.namelist():
            if member.startswith(archive_dir + "/") and not member.endswith("/"):
                # Replace archive_dir prefix with target_dir one
                relative_path = member[len(archive_dir) + 1:]
                target_path = Path(output_dir, relative_path)
                os.makedirs(target_path.parent, exist_ok=True)
                with zip_file.open(member) as src, open(target_path, "wb") as dst:
                    # supress the warning as the result of open() actually is a BufferedWriter
                    shutil.copyfileobj(src, dst)  # type: ignore[arg-type]


class ChromeDownloader:
    """
        Download and unpack latest stable Chrome driver and Chrome
    """

    class Component(StrEnum):
        """
        Component name
        """
        CHROME = 'chrome'
        CHROMEDRIVER = 'chromedriver'

    def __init__(self, platform_name: str) -> None:
        self.platform_name = platform_name
        self._downloads = None

    @property
    def downloads(self) -> dict[str, Any]:
        """
        Latest available stable downloads

        :return: Dictionary containing downloads info
        """
        if not self._downloads:
            response = requests.get(CHROME_API_ENDPOINT_URL)
            response.raise_for_status()
            data = response.json()
            self._downloads = data['channels']['Stable']['downloads']
        return self._downloads

    def download_all(self, chromedriver_root: str | Path, chrome_subdir: str | Path) -> None:
        """
        Downloads all components (Chrome driver and Chrome) into directories provided. Target directory tree will be:

        <chromedriver_root>/
            ├── chromedriver[.exe]
            └── <chrome_subdir>/
                ├── [chrome files]
                └── chrome[.exe]

        :param chromedriver_root: root directory where Chrome driver will be placed
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
        response = requests.get(url)
        response.raise_for_status()
        archive_dir = f'{what}-{self.platform_name}'

        unpack(response.content, archive_dir, where)
