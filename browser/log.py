"""
    Browser logging setup
"""
import inspect
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import cast, TYPE_CHECKING, Iterator, TypeAlias

from .logconfig import LOG_CONFIG

if TYPE_CHECKING:
    from .browser import Browser

TRACE = 5
logging.addLevelName(TRACE, "TRACE")

ExcInfo: TypeAlias = (
        bool
        | tuple[type[BaseException], BaseException, TracebackType | None]
        | tuple[None, None, None]
        | BaseException
)


class WebLogger(logging.Logger):
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

    Instance attributes:
        _base_dir: Logger base directory
    Class attributes:
        _INITIALIZED_LEVEL_DIRS (set): Track per-level directories creation status
        _BROWSER: Browser instance
        _GROUP_NAME: log group name
        _COUNTERS: Per-level and group log counter
    """
    TRACE = 'trace'
    ERROR = 'error'
    _PNG = '.png'
    _HTML = '.html'
    _ENCODING = 'utf-8'
    _INITIALIZED_LEVEL_DIRS: set[str] = set()  # which logging subdirs were rotated and/or initialized in this run
    _BROWSER: 'Browser | None' = None
    _GROUP_NAME: str | None = None
    _COUNTERS: dict[str, int] = {}  # per logging level counter (trace/error)

    def __init__(self, name: str, base_dir: str | Path = "."):
        """
        Creates a new web logger object
        :param name: logger name
        :param base_dir: log base directory
        """
        self._callstack_level: int | None = None
        self._base_dir = Path(base_dir)

        super().__init__(name)

    # --- public API ---

    def trace(self,
              message: object,
              *args: object,
              exc_info: ExcInfo | None = None,
              stack_info: bool = False,
              stacklevel: int = 1,
              extra: dict[str, object] | None = None) -> None:
        """
        Log a message at TRACE level.

        :param message: log text
        :param args: formatting arguments
        :param exc_info: exception details
        :param stack_info: whether to include stack information
        :param stacklevel: stack frame depth
        :param extra: extra context data
        """
        if self.isEnabledFor(TRACE):
            self._log(TRACE, message, args, exc_info, extra, stack_info, stacklevel)

    def web_error(self) -> None:
        """
        Always capture into 'error' dir.
        """
        if WebLogger._BROWSER is None:
            raise RuntimeError('Cannot create web logs: browser is not set.')
        self._capture(self.ERROR)

    def web_trace(self, reason: str) -> None:
        """
        Capture into 'trace' dir only if enabled.
        :param reason: Logging event reason
        """
        if WebLogger._BROWSER is None:
            raise RuntimeError('Cannot create web logs: browser is not set.')
        if WebLogger._BROWSER.options.save_trace_logs:
            self._capture(self.TRACE, reason=reason)

    @classmethod
    @contextmanager
    def browser(cls, browser: 'Browser') -> Iterator[None]:
        """
        Set browser context
        :param browser: Browser instance
        """
        try:
            cls._BROWSER = browser
            yield
        finally:
            cls._BROWSER = None

    @classmethod
    @contextmanager
    def group(cls, name: str) -> Iterator[None]:
        """
        Yield web logs grouped by the given name.

        :param name: grouping key
        """
        try:
            cls._GROUP_NAME = name
            cls._COUNTERS = {}
            yield
        finally:
            cls._GROUP_NAME = None

    # --- internals ---
    def _name(self) -> str:
        return self._GROUP_NAME or self.name

    def _capture(self, level: str, reason: str = "") -> None:
        """
        Non-fatal capture: returns None on any FS/browser exception.
        Useful if you don't want tracing to fail tests.
        :param level: Logging level
        :param reason: Logging event reason
        :return: WebArtifact or None exception occured during logging
        """
        try:
            if WebLogger._BROWSER is None:
                raise RuntimeError('Cannot create web logs: browser is not set.')
            target_dir = self._get_logger_dir(level, self._name())
            filename = self._next_filename(level=level, reason=reason)

            full_path = target_dir / filename
            png = Path(f'{full_path}{self._PNG}')
            html = Path(f'{full_path}{self._HTML}')

            # Actual writes:
            WebLogger._BROWSER.save_screenshot(str(png))
            html.write_text(WebLogger._BROWSER.page_source, encoding=self._ENCODING)

        except OSError:
            log.exception('Cannot create log entry')
        return None

    def _get_first_external_frame(self) -> inspect.FrameInfo:
        """
            Get first external call frame (e.g. outside WebLogger object)
        """
        stack = inspect.stack()
        if self._callstack_level is None:
            level = 0
            f_locals = stack[level].frame.f_locals
            while f_locals.get('self') == self:
                level += 1
                f_locals = stack[level].frame.f_locals
            self._callstack_level = level
        return stack[self._callstack_level]

    def _get_caller(self) -> str:
        """
            Determine the function that triggered the log message.
        """
        # get callers name of the requested level

        frame_info = self._get_first_external_frame()

        # get the class name if available
        class_name = f"{frame_info.frame.f_locals['self'].__class__.__name__}_" \
            if 'self' in frame_info.frame.f_locals else ""

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
            return self._base_dir / level
        return self._base_dir / level / logger_name

    def _get_logger_dir(self, level: str, logger_name: str) -> Path:
        """
        Lazily rotate and create the directory used for this run.
        Rotation happens at most once per level ("trace"/"error") per process run.
        :param level: Logging level
        :param logger_name: Logger name
        :return logging directory for specified level and logger name
        """
        if level not in self._INITIALIZED_LEVEL_DIRS:
            # IMPORTANT: rotate the ROOT subdir (base_dir/subdir), not the per-name subdir.
            # Your old code rotated "trace" but then wrote into "trace/<name>" - that is fine,
            # but make sure you rotate the same thing you expect.
            level_dir = self._base_dir / level

            if level_dir.exists() and level_dir.is_dir():
                last = self._find_last_rotation(level=level)
                dst = self._base_dir / f"{level}.{last + 1:03d}"
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
        if not self._base_dir.exists():
            return 0

        for p in self._base_dir.iterdir():
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
        self._COUNTERS[level] = self._COUNTERS.get(level, 0) + 1
        return self._COUNTERS[level]

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


def _setup_handler(handler: logging.Handler,
                   level: str,
                   formatting: str) -> logging.Handler:
    """
        Configure a logging handler with predefined formatting.
    """
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(formatting))
    return handler


def setup_logging(name: str) -> WebLogger:
    """
    Setup browser logging

    :param name: log name

    :return: logger object
    """
    logging.setLoggerClass(WebLogger)
    logger = cast(WebLogger, logging.getLogger(name))
    logger.setLevel(LOG_CONFIG.level)
    if logger.hasHandlers():
        logger.handlers.clear()
    handlers = []
    if LOG_CONFIG.console:
        handlers.append(_setup_handler(logging.StreamHandler(),
                                       LOG_CONFIG.level,
                                       LOG_CONFIG.formatting))
    if LOG_CONFIG.file:
        if not LOG_CONFIG.initialized and os.path.exists(LOG_CONFIG.file):
            os.remove(LOG_CONFIG.file)
        handlers.append(_setup_handler(logging.FileHandler(LOG_CONFIG.file, encoding='utf-8'),
                                       LOG_CONFIG.level,
                                       LOG_CONFIG.formatting))
    for handler in handlers:
        logger.addHandler(handler)

    LOG_CONFIG.initialized = True
    return logger


log = setup_logging(__name__)
