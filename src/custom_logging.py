import logging.config
import os

CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(levelname)s %(asctime)s %(filename)s->%(funcName)s->%(lineno)d : %(message)s",
            "datefmt": "%y/%m/%d %H:%M:%S",
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "stderr": {
            "class": "logging.StreamHandler",
            "level": "ERROR",
            "formatter": "simple",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "simple",
            "filename": os.path.join(os.path.dirname(__file__), "..", "local_log.log"),
            "mode": "a",
        },
    },
    "root": {"level": "DEBUG", "handlers": ["stderr", "stdout", "file"]},
}


def is_logging_configured():
    # Check if the root logger has any handlers explicitly assigned
    return len(logging.getLogger().handlers) >= 3


def setup_logging():
    if not is_logging_configured():
        logging.config.dictConfig(CONFIG)
        logging.getLogger("py4j").setLevel(logging.ERROR)
    return logging
