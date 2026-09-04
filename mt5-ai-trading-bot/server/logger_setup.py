"""File logger with rotation: writes both console and file copies."""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = 'mt5ai', log_dir: str = None) -> logging.Logger:
    log_dir = log_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f'{name}.log')

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # file handler (rotating, 2 MB x 5)
    fh = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=5,
                             encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # console
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger
