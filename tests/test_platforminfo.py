"""
    Platforminfo tests
"""
import platform
import sys

import pytest
from _pytest.monkeypatch import MonkeyPatch

import browser.platforminfo as platforminfo


@pytest.mark.parametrize(
    "sysname,machine,expected",
    [
        ("Linux", "x86_64", "linux64"),
        ("Linux", "aarch64", "linux64"),  # 32-bit Linux is not supported
        ("Darwin", "arm64", "mac-arm64"),
        ("Darwin", "ARM64", "mac-arm64"),  # case-insensitive
        ("Darwin", "x86_64", "mac-x64"),
        ("Darwin", "i386", "mac-x64"),
        ("FreeBSD", "x86_64", platforminfo.PlatformInfo.unknown),
    ],
)
def test_platform_mapping_non_windows(monkeypatch: MonkeyPatch, sysname: str, machine: str, expected: str) -> None:
    monkeypatch.setattr(platform, "system", lambda: sysname)
    monkeypatch.setattr(platform, "machine", lambda: machine)

    pi = platforminfo.PlatformInfo()
    assert pi.system == sysname
    assert pi.platform == expected


@pytest.mark.parametrize(
    "maxsize,expected",
    [
        (2**63 - 1, "win64"),
        (2**31 - 1, "win32"),
        (2**31, "win32"),
        (2**31 + 1, "win64"),
        (2**32 + 1, "win64"),
    ],
)
def test_platform_mapping_windows(monkeypatch: MonkeyPatch, maxsize: int, expected: str) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(sys, "maxsize", maxsize)

    pi = platforminfo.PlatformInfo()
    assert pi.platform == expected


def test_system_is(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")

    pi = platforminfo.PlatformInfo()
    assert pi.system_is("Linux")
    assert pi.system_is("Windows", "Linux")
    assert not pi.system_is("Darwin")
