# -*- coding: utf-8 -*-
"""Helper utilities for logging."""
from __future__ import annotations

import datetime
import logging
import os
import sys
import time
from typing import Any
from typing import List
from typing import Optional

from .exceptions import LogFolderDoesNotExistError
from .exceptions import LogFolderGivenWithoutFilePrefixError
from .exceptions import UnrecognizedLoggingFormatError


def configure_logging(
    path_to_log_folder: Optional[str] = None,
    log_file_prefix: Optional[str] = None,
    log_level: int = logging.INFO,
    logging_format: str = "standard",
    logging_formatter: Optional[logging.Formatter] = None,
) -> None:
    """Apply standard configuration to logging.

    Args:
        path_to_log_folder: optional path to an existing folder in which a log file will be created and used instead of stdout. log_file_prefix must also be specified if this argument is not None.
        log_file_prefix: if path_to_log_folder is specified, will write logs to file in the given log folder using this as the prefix of the filename.
        log_level: set the desired logging threshold level
        logging_format: the desired format of logging output. 'standard' should be used in all cases except for when used in a notebook.
        logging_formatter: optional custom formatter to set on each logging handler. Useful as a catch-all in situations where information must be redacted from log files.
    """
    logging.Formatter.converter = time.gmtime  # ensure all logging timestamps are UTC

    handlers: List[Any] = list()
    if path_to_log_folder is not None:
        if log_file_prefix is None:
            raise LogFolderGivenWithoutFilePrefixError()
        if not os.path.isdir(path_to_log_folder):
            raise LogFolderDoesNotExistError(path_to_log_folder)
        file_handler = logging.FileHandler(
            os.path.join(
                path_to_log_folder,
                f'{log_file_prefix}__{datetime.datetime.utcnow().strftime("%Y_%m_%d_%H%M%S")}.txt',
            )
        )
        handlers.append(file_handler)
    else:
        handlers.append(logging.StreamHandler(sys.stdout))

    if logging_format == "standard":
        config_format = "[%(asctime)s UTC] %(name)s-{%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
    elif logging_format == "notebook":
        config_format = "[%(asctime)s UTC] %(levelname)s - %(message)s"
    else:
        raise UnrecognizedLoggingFormatError(logging_format)

    if logging_formatter is not None:
        for handler in handlers:
            handler.setFormatter(logging_formatter)

    logging.basicConfig(
        level=log_level,
        format=config_format,
        handlers=handlers,
    )
