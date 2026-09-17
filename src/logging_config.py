"""
Nothing runs at import time. :func:`setup_logging` configures the root
logger, which is a decision only an entry point gets to make, so it is called
from the console-script wrappers in ``loader``/``manipulator`` and from the test
session's ``conftest``.
"""

import logging.config
import os

LOG_FILE_ENV_VAR = "CMS_PIPELINE_LOG_FILE"
DEFAULT_LOG_FILENAME = "local_log.log"

FORMAT = (
    "%(levelname)s %(asctime)s %(filename)s->%(funcName)s->%(lineno)d : %(message)s"
)


def get_log_file_path() -> str:
    return os.environ.get(
        LOG_FILE_ENV_VAR, os.path.join(os.getcwd(), DEFAULT_LOG_FILENAME)
    )


def build_config() -> dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": FORMAT,
                "datefmt": "%y/%m/%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stderr",
            },
            # no level, so the file keeps the DEBUG records the console drops.
            "file": {
                "class": "logging.FileHandler",
                "formatter": "simple",
                "filename": get_log_file_path(),
                "mode": "a",
            },
        },
        "root": {"level": "DEBUG", "handlers": ["console", "file"]},
    }


def is_logging_configured() -> bool:
    """
    whether anything has already claimed the root logger.
    """
    return bool(logging.getLogger().handlers)


def setup_logging() -> None:
    if not is_logging_configured():
        logging.config.dictConfig(build_config())
        logging.getLogger("py4j").setLevel(logging.ERROR)
