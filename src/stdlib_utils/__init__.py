# -*- coding: utf-8 -*-
"""Helper utilities only requiring the standard library."""
from __future__ import annotations

from . import checksum
from . import loggers
from . import misc
from . import parallelism_utils
from . import ports
from . import queue_utils
from .checksum import compute_crc32_and_write_to_file_head
from .checksum import compute_crc32_bytes_of_large_file
from .checksum import compute_crc32_hex_of_large_file
from .checksum import validate_file_head_crc32
from .constants import NANOSECONDS_PER_CENTIMILLISECOND
from .constants import QUEUE_CHECK_TIMEOUT_SECONDS
from .constants import SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE
from .constants import UnionOfThreadingAndMultiprocessingQueue
from .exceptions import BadQueueTypeError
from .exceptions import BlankAbsoluteResourcePathError
from .exceptions import Crc32ChecksumValidationFailureError
from .exceptions import Crc32InFileHeadDoesNotMatchExpectedValueError
from .exceptions import LogFolderDoesNotExistError
from .exceptions import LogFolderGivenWithoutFilePrefixError
from .exceptions import MultipleMatchingXmlElementsError
from .exceptions import NoMatchingXmlElementError
from .exceptions import ParallelFrameworkStillNotStoppedError
from .exceptions import PortNotInUseError
from .exceptions import PortUnavailableError
from .exceptions import QueueNotEmptyError
from .exceptions import QueueNotExpectedSizeError
from .exceptions import QueueStillEmptyError
from .exceptions import UnrecognizedLoggingFormatError
from .loggers import configure_logging
from .misc import create_directory_if_not_exists
from .misc import get_current_file_abs_directory
from .misc import get_current_file_abs_path
from .misc import get_formatted_stack_trace
from .misc import get_path_to_frozen_bundle
from .misc import is_frozen_as_exe
from .misc import is_system_windows
from .misc import print_exception
from .misc import resource_path
from .misc import sort_nested_dict
from .multiprocessing_utils import InfiniteProcess
from .parallelism_framework import InfiniteLoopingParallelismMixIn
from .parallelism_utils import confirm_parallelism_is_stopped
from .parallelism_utils import invoke_process_run_and_check_errors
from .parallelism_utils import put_log_message_into_queue
from .ports import confirm_port_available
from .ports import confirm_port_in_use
from .ports import is_port_in_use
from .queue_utils import confirm_queue_is_eventually_empty
from .queue_utils import confirm_queue_is_eventually_of_size
from .queue_utils import drain_queue
from .queue_utils import is_queue_eventually_empty
from .queue_utils import is_queue_eventually_not_empty
from .queue_utils import is_queue_eventually_of_size
from .queue_utils import put_object_into_queue_and_raise_error_if_eventually_still_empty
from .queue_utils import safe_get
from .queue_utils import SimpleMultiprocessingQueue
from .queue_utils import TestingQueue
from .threading_utils import InfiniteThread
from .xml import find_exactly_one_xml_element

__all__ = [
    "configure_logging",
    "resource_path",
    "is_frozen_as_exe",
    "get_formatted_stack_trace",
    "get_path_to_frozen_bundle",
    "is_system_windows",
    "create_directory_if_not_exists",
    # "raise_alarm_signal",
    "misc",
    "checksum",
    "loggers",
    "InfiniteProcess",
    "SimpleMultiprocessingQueue",
    "invoke_process_run_and_check_errors",
    "find_exactly_one_xml_element",
    "MultipleMatchingXmlElementsError",
    "NoMatchingXmlElementError",
    "ports",
    "confirm_port_in_use",
    "confirm_port_available",
    "is_queue_eventually_empty",
    "is_queue_eventually_not_empty",
    "confirm_queue_is_eventually_empty",
    "put_object_into_queue_and_raise_error_if_eventually_still_empty",
    "QueueStillEmptyError",
    "is_port_in_use",
    "PortUnavailableError",
    "PortNotInUseError",
    "BlankAbsoluteResourcePathError",
    "InfiniteThread",
    "InfiniteLoopingParallelismMixIn",
    "put_log_message_into_queue",
    "confirm_parallelism_is_stopped",
    "ParallelFrameworkStillNotStoppedError",
    "print_exception",
    "get_current_file_abs_directory",
    "get_current_file_abs_path",
    "parallelism_utils",
    "safe_get",
    "drain_queue",
    "LogFolderGivenWithoutFilePrefixError",
    "LogFolderDoesNotExistError",
    "compute_crc32_bytes_of_large_file",
    "compute_crc32_hex_of_large_file",
    "compute_crc32_and_write_to_file_head",
    "validate_file_head_crc32",
    "Crc32InFileHeadDoesNotMatchExpectedValueError",
    "Crc32ChecksumValidationFailureError",
    "UnrecognizedLoggingFormatError",
    "queue_utils",
    "is_queue_eventually_of_size",
    "SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE",
    "confirm_queue_is_eventually_of_size",
    "QueueNotExpectedSizeError",
    "QueueNotEmptyError",
    "UnionOfThreadingAndMultiprocessingQueue",
    "QUEUE_CHECK_TIMEOUT_SECONDS",
    "NANOSECONDS_PER_CENTIMILLISECOND",
    "TestingQueue",
    "BadQueueTypeError",
    "sort_nested_dict",
]
