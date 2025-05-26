"""Logs for web page operations"""
import inspect
import os
from datetime import datetime


def _get_caller(level: int = 3) -> str:
    """
        Determine the function that triggered the log message.
    """
    # get callers name of the requested level
    frame = inspect.stack()[level].frame

    # get method name
    method_name = inspect.stack()[level].function

    # get the class name if available
    class_name = None
    if 'self' in frame.f_locals:
        class_name = frame.f_locals['self'].__class__.__name__

    return f'{class_name}_{method_name}'



class WebLogger:
    """
    Handles logging operations for web activities.

    This class is designed to facilitate the management and storage of log files,
    screenshots, and HTML page sources generated during web activities. It organizes
    logs into specific directories based on the type of log, such as errors or traces,
    and appends useful metadata like timestamps and caller details to the filenames.
    The service ensures directory organization and log uniqueness by performing checks
    and renaming existing directories.

    Attributes:
        root_dir (set): A class-level attribute used to track directories already created
            during the logging process.
    """
    root_dir = set()

    def __init__(self, name: str):
        """
            Initialize logger instance with service name context.
        """
        self.browser = None
        self.name = name
        self.trace_id = {}

    @classmethod
    def _path_already_created(cls, subdir: str) -> bool:
        """
        Check if a log path was already created to avoid duplication.
        - If the path exists, return True
        - If the path does not exist, add it to the root_dir set and return False
        :param subdir: path to check
        :return: True if path already exists, False if not.
        """
        if subdir in cls.root_dir:
            return True
        cls.root_dir.add(subdir)
        return False

    def _get_dir(self, level: str) -> str:
        """
        Create a per-class directory structure for trace logs but keep error logs for all classes in the same directory.
        :param level: debug level name
        :return: logs dir
        """
        if level != "error":
            return os.path.join(level, self.name)
        return level

    def _get_filename(self, subdir: str, suffix: str = "") -> str:
        """
            Generate a structured filename for the log output.
        """
        self.trace_id[subdir] = self.trace_id.get(subdir, 0) + 1
        timestamp = datetime.today().isoformat(sep=' ', timespec='milliseconds').replace(':', '-')
        filename = f"{self.trace_id[subdir]:0>3} {timestamp} {_get_caller()} {suffix}".strip()
        if not self._path_already_created(subdir):
            if os.path.exists(subdir):
                last_number = max([int(d.split('.')[1]) if '.' in d else 0
                                   for d in os.listdir()
                                   if d.startswith(f"{subdir}") and os.path.isdir(d)], default=0)
                os.rename(subdir, f'{subdir}.{last_number + 1:>03}')
        subdir = self._get_dir(subdir)
        os.makedirs(subdir, exist_ok=True)
        return os.path.join(subdir, filename)

    def trace(self, suffix: str) -> None:
        """
        Trace logs based on the provided suffix if logging is enabled.

        This method checks if trace logging is enabled via the `save_trace_logs`
        attribute of the browser instance. When enabled, it generates a proper
        filename using the suffix provided, writes the trace logs, and saves
        them to the specified file.

        Args:
            suffix: A string used to customize or identify the generated filename
            for the trace logs.

        Returns:
            None

        Raises:
            None
        """
        if self.browser.save_trace_logs:
            filename = self._get_filename("trace", suffix)
            self._write_logs(filename)

    def error(self) -> None:
        """
        Logs error messages by generating a filename using the _get_filename method
        and writing logs to the generated file.

        Returns:
            None

        Raises:
            None
        """
        filename = self._get_filename("error")
        self._write_logs(filename)

    def _write_logs(self, filename: str):
        """
            Generate a structured filename for the log output.
        """
        self.browser.save_screenshot(f"{filename}.png")
        with open(f"{filename}.html", "w", encoding="utf-8") as page_source_file:
            page_source_file.write(self.browser.page_source)
