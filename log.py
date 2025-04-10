import logging


def setup_logging(name, level, formatting="%(levelname)s:%(name)s %(asctime)s %(message)s"):
    log = logging.getLogger(name)
    log.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(formatting))
    log.addHandler(ch)
    return log


setup_logging(__name__, logging.DEBUG)
