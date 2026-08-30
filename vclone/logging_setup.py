import logging
import os
from logging.handlers import RotatingFileHandler

from . import config


def _build_logger():
    os.makedirs(config.LOG_DIR, exist_ok=True)

    logger = logging.getLogger("viclone")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = RotatingFileHandler(
        os.path.join(config.LOG_DIR, "viclone.log"), maxBytes=2_000_000, backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = _build_logger()
