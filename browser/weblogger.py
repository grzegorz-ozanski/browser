"""Logs for web page operations"""
import inspect
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from browser import Browser, setup_logging

log = setup_logging(__name__)


@dataclass(frozen=True)
class WebArtifact:
    """
    Web logger artifact.
    """
    base: Path  # without suffix
    png: Path
    html: Path
    subdir: str  # "trace" / "error"
    name: str  # service/provider name (your self.name)
    suffix: str


class WebLogger:
    """
    Handles logging operations for web activities.

    This class is designed to facilitate the management and storage of log files,
    screenshots, and HTML page sources generated during web activities. It organizes
    logs into specific directories based on the type of log, such as errors or traces,
    and appends useful metadata like timestamps and caller details to the filenames.
    The service ensures directory organization and log uniqueness by performing checks
    and renaming existing directories.

    Directory layout:
      - trace/<name>/...  (per-class/per-provider)
      - error/...         (shared)

    Rotation:
      - if 'trace' dir exists, it is renamed to 'trace.###' ON FIRST WRITE in this run
      - same for 'error'

    Attributes:
        browser: WebBrowser instance used to capture screenshots and sources
        name: Logger name
        base_dir: Logger base directory
        _INITIALIZED_LEVEL_DIRS (set): A class-level attribute used to track per-level directories creation status
        _counters: Per-level directory
    """
    """
    Stores screenshots + page sources in a structured directory hierarchy.

    """
    TRACE = 'trace'
    ERROR = 'error'
    _PNG = '.png'
    _HTML = '.html'
    _ENCODING = 'utf-8'
    _INITIALIZED_LEVEL_DIRS: set[str] = set()  # which logging subdirs were rotated and/or initialized in this run
    _CALLSTACK_LEVEL: int | None = None

    def __init__(self, name: str, browser: Browser, base_dir: str | Path = "."):
        """
        Creates a new web logger object
        :param name: logger name
        :param browser: browser instance used to capture screenshots and sources
        :param base_dir: log base directory
        """
        self.browser = browser
        self.name = name
        self.base_dir = Path(base_dir)

        self._counters: dict[str, int] = {}  # per logging level counter (trace/error)

    # --- public API ---

    def error(self) -> WebArtifact | None:
        """
        Always capture into 'error' dir.
        :return: WebArtifact
        """
        return self.capture(self.ERROR)

    def trace(self, reason: str) -> WebArtifact | None:
        """
        Capture into 'trace' dir only if enabled.
        :param reason: Logging event reason
        :return: WebArtifact or None if trace logs are disabled
        """
        if not self.browser.options.save_trace_logs:
            return None
        return self.capture(self.TRACE, reason=reason)

    def capture(self, level: str, reason: str = "") -> WebArtifact | None:
        """
        Non-fatal capture: returns None on any FS/browser exception.
        Useful if you don't want tracing to fail tests.
        :param level: Logging level
        :param reason: Logging event reason
        :return: WebArtifact or None exception occured during logging
        """
        try:
            target_dir = self._get_logger_dir(level, self.name)
            filename = self._next_filename(level=level, reason=reason)

            full_path = target_dir / filename
            png = Path(f'{full_path}{self._PNG}')
            html = Path(f'{full_path}{self._HTML}')

            # Actual writes:
            self.browser.save_screenshot(str(png))
            html.write_text(self.browser.page_source, encoding=self._ENCODING)

            return WebArtifact(
                base=full_path,
                png=png,
                html=html,
                subdir=level,
                name=self.name,
                suffix=reason,
            )
        except OSError:
            log.exception('Cannot create log entry')
        return None


    # --- internals ---
    def _get_first_external_frame(self) -> inspect.FrameInfo:
        """
            Get first external call frame (e.g. outside WebLogger object)
        """
        stack = inspect.stack()
        if self._CALLSTACK_LEVEL is None:
            level = 0
            f_locals = stack[level].frame.f_locals
            while f_locals.get('self') == self:
                level += 1
                f_locals = stack[level].frame.f_locals
            self._CALLSTACK_LEVEL = level
        return stack[self._CALLSTACK_LEVEL]

    def _get_caller(self) -> str:
        """
            Determine the function that triggered the log message.
        """
        # get callers name of the requested level

        frame_info = self._get_first_external_frame()

        # get the class name if available
        class_name = f"{frame_info.frame.f_locals['self'].__class__.__name__}_" if 'self' in frame_info.frame.f_locals else ""

        return f'{class_name}{frame_info.function}'

    def _resolve_dir(self, level: str, logger_name: str) -> Path:
        """
        Return log directory::
          - trace -> trace/<name>
          - error -> error
        :param level: Logging level
        :param logger_name: Logger name
        :return logging directory for specified level and logger name
        """
        if level == self.ERROR:
            return self.base_dir / level
        return self.base_dir / level / logger_name

    def _get_logger_dir(self, level: str, logger_name: str) -> Path:
        """
        Lazily rotate and create the directory used for this run.
        Rotation happens once per subdir per instance.
        :param level: Logging level
        :param logger_name: Logger name
        :return logging directory for specified level and logger name
        """
        if level not in self._INITIALIZED_LEVEL_DIRS:
            # IMPORTANT: rotate the ROOT subdir (base_dir/subdir), not the per-name subdir.
            # Your old code rotated "trace" but then wrote into "trace/<name>" - that is fine,
            # but make sure you rotate the same thing you expect.
            level_dir = self.base_dir / level

            if level_dir.exists() and level_dir.is_dir():
                last = self._find_last_rotation(level=level)
                dst = self.base_dir / f"{level}.{last + 1:03d}"
                level_dir.rename(dst)

        # Create active directory (per-name for trace, shared for error)
        logger_dir = self._resolve_dir(level, logger_name)
        logger_dir.mkdir(parents=True, exist_ok=True)

        self._INITIALIZED_LEVEL_DIRS.add(level)
        return logger_dir

    def _find_last_rotation(self, level: str) -> int:
        """
        Find the biggest N in 'subdir.NNN' under base_dir for the specified logging level.
        :param level: Logging level
        :return biggest N in 'subdir.NNN' under base_dir
        """
        prefix = f"{level}."
        last = 0
        if not self.base_dir.exists():
            return 0

        for p in self.base_dir.iterdir():
            if not p.is_dir():
                continue
            name = p.name
            if not name.startswith(prefix):
                continue
            tail = name[len(prefix):]
            if len(tail) != 3:
                continue
            try:
                n = int(tail)
            except ValueError:
                continue
            last = max(last, n)
        return last

    def _next_id(self, level: str) -> int:
        """
        Calculate next id of the file for the specified logging level.
        :param level:logging level
        :return: numeric file id
        """
        self._counters[level] = self._counters.get(level, 0) + 1
        return self._counters[level]

    def _next_filename(self, level: str, reason: str) -> str:
        """
        Build filename stem (without extension).
        :param level: logging level
        :param reason: logging message (reason)
        :return filename stem (without extension)
        """
        i = self._next_id(level)
        ts = datetime.today().isoformat(sep=" ", timespec="milliseconds").replace(":", "-")
        caller = self._get_caller()
        return f"{i:03d} {ts} {caller} {reason}".strip()
