import inspect
import os
from datetime import datetime


def _get_caller(level: int = 3) -> str:
    # get callers name of the requested level
    frame = inspect.stack()[level].frame

    # get method name
    method_name = inspect.stack()[level].function

    # get class name if available
    class_name = None
    if 'self' in frame.f_locals:
        class_name = frame.f_locals['self'].__class__.__name__

    return f'{class_name}_{method_name}'



class TraceLogger:
    root_dir = set()

    def __init__(self, service_name: str):
        self.browser = None
        self.service_name = service_name
        self.trace_id = {}

    @classmethod
    def _path_already_created(cls, subdir: str) -> bool:
        if subdir in cls.root_dir:
            return True
        cls.root_dir.add(subdir)
        return False

    def _get_filename(self, subdir: str, suffix: str = "") -> str:
        self.trace_id[subdir] = self.trace_id.get(subdir, 0) + 1
        timestamp = datetime.today().isoformat(sep=' ', timespec='milliseconds').replace(':', '-')
        filename = f"{self.trace_id[subdir]:0>3} {timestamp} {_get_caller()} {suffix}".strip()
        if not self._path_already_created(subdir):
            if os.path.exists(subdir):
                last_number = max([int(d.split('.')[1]) if '.' in d else 0
                                   for d in os.listdir()
                                   if d.startswith(f"{subdir}") and os.path.isdir(d)], default=0)
                os.rename(subdir, f'{subdir}.{last_number + 1:>03}')
        if subdir != "error":
            subdir = os.path.join(subdir, self.service_name)
        os.makedirs(subdir, exist_ok=True)
        return os.path.join(subdir, filename)

    def trace(self, suffix: str) -> None:
        if self.browser.save_trace_logs:
            filename = self._get_filename("trace", suffix)
            self._write_logs(filename)

    def error(self) -> None:
        filename = self._get_filename("error")
        self._write_logs(filename)

    def _write_logs(self, filename: str):
        self.browser.save_screenshot(f"{filename}.png")
        with open(f"{filename}.html", "w", encoding="utf-8") as page_source_file:
            page_source_file.write(self.browser.page_source)
