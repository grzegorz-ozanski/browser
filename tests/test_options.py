import itertools
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch
import browser.platforminfo as platforminfo
from browser import UserAgent
from browser.options import BrowserOptions, PROFILE_NAME

BASE = dict(
    root_path=__file__,
    chrome_path='',
    persistent_profile_dir='',
    timeout=10,
    renderer_timeout=30,
)


def build_parameters():
    for headless, trace, persistent_profile, system, profile_name in itertools.product(
        [True, False],
        [True, False],
        [True, False],
        ['Linux', 'Windows'],
        ['test_profile', None]
    ):
        yield Parameters(
            **BASE,
            headless=headless,
            save_trace_logs=trace,
            persistent_profile=persistent_profile,
            system=system,
            profile_name=profile_name
        )


@dataclass
class Parameters:
    """
    Browser options parameters
    """
    root_path: str
    headless: bool
    save_trace_logs: bool
    chrome_path: str
    persistent_profile: bool
    persistent_profile_dir: str
    timeout: int
    renderer_timeout: int
    system: str
    profile_name: str


@pytest.mark.parametrize(
    "parameters", list(build_parameters()),
)
def test_options(monkeypatch: MonkeyPatch, parameters: Parameters) -> None:
    monkeypatch.setattr(platforminfo.platform, "system", lambda: parameters.system)
    kwargs = dict(
        root_path=parameters.root_path,
        headless=parameters.headless,
        save_trace_logs=parameters.save_trace_logs,
        chrome_path=parameters.chrome_path,
        persistent_profile=parameters.persistent_profile,
        persistent_profile_dir=parameters.persistent_profile_dir,
        timeout=parameters.timeout,
        renderer_timeout=parameters.renderer_timeout
    )
    if parameters.profile_name:
        kwargs['profile_name'] = parameters.profile_name
    options = BrowserOptions(**kwargs)
    for attr in ['headless', 'save_trace_logs', 'timeout', 'renderer_timeout']:
        assert getattr(options, attr) == getattr(parameters, attr)

    driver_options = ['disable-blink-features=AutomationControlled',
                      'window-size=1920,1200',
                      'log-level=3',
                      'disable-dev-shm-usage',
                      'remote-debugging-pipe']
    if parameters.system == 'Linux':
        driver_options += ['no-sandbox']
    if parameters.headless:
        driver_options += ['headless']

    assert options._driver_options == driver_options
    ua = UserAgent(parameters.system)
    profile_name = PROFILE_NAME if parameters.profile_name is None else parameters.profile_name
    driver_options += [f'user-data-dir={Path(tempfile.gettempdir()) / profile_name}',
                       f'user-agent={ua.current}']
    assert options.driver_options == driver_options
    str_options = str(options)
    assert str_options != ''
    for key, value in options.__dict__.items():
        assert key + '=' + str(value) in str_options
