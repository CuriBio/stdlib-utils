# -*- coding: utf-8 -*-
"""Helper utilities for logging."""
from __future__ import annotations

import datetime
import logging
import os
import sys
import time
from typing import Optional

from .exceptions import LogFolderDoesNotExistError
from .exceptions import LogFolderGivenWithoutFilePrefixError
from .exceptions import UnrecognizedLoggingFormatError
from .misc import create_directory_if_not_exists
from .misc import resource_path


def configure_logging(
    path_to_log_folder: Optional[str] = None,
    log_file_prefix: Optional[str] = None,
    log_level: int = logging.INFO,
    logging_format: str = "standard",
    logging_formatter: Optional[logging.Formatter] = None,
) -> None:
    """Apply standard configuration to logging.

    Args:
        path_to_log_folder: optional path to an exisiting folder to use for creating log files. log_file_prefix must also be specified if this argument is not None.
        log_file_prefix: if set without path_to_log_folder specified, will write logs to file in a subfolder (logs). By default it will create a subfolder in the current working directory (if running from source) or in the path that the EXE was installed to for pyinstaller. If path_to_log_folder is specified will write logs to file in the given log folder using this as the prefix.
        log_level: set the desired logging threshold level
        logging_format: the desired format of logging output. 'standard' should be used in all cases except for when used in a notebook.
        logging_formatter: optional custom formatter to set on each logging handler. Useful as a catch-all in situations where information must be redacted from log files.
    """
    logging.Formatter.converter = time.gmtime  # ensure all logging timestamps are UTC
    stdout_handler = logging.StreamHandler(sys.stdout)
    handlers = [stdout_handler]
    if log_file_prefix is not None:
        log_folder: str
        if path_to_log_folder is not None:
            if not os.path.isdir(path_to_log_folder):
                raise LogFolderDoesNotExistError(path_to_log_folder)
            log_folder = path_to_log_folder
        else:
            log_folder = resource_path("logs", base_path=os.getcwd())
            create_directory_if_not_exists(log_folder)
        file_handler = logging.FileHandler(
            os.path.join(
                log_folder,
                f'{log_file_prefix}__{datetime.datetime.utcnow().strftime("%Y_%m_%d_%H%M%S")}.txt',
            )
        )
        handlers.append(file_handler)
    elif path_to_log_folder is not None:
        raise LogFolderGivenWithoutFilePrefixError()

    config_format: str
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
