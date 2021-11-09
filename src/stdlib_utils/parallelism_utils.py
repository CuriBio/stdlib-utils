# -*- coding: utf-8 -*-
"""Functionality to enhance parallelism.

This module can import things from threading_utils,
multiprocessing_utils, and queue_utils.
"""
from __future__ import annotations

import multiprocessing
import multiprocessing.queues
from queue import Queue
from time import perf_counter
from time import sleep
from typing import Any
from typing import Dict
from typing import Optional
from typing import Union

from .exceptions import ParallelFrameworkStillNotStoppedError
from .multiprocessing_utils import InfiniteProcess
from .parallelism_framework import InfiniteLoopingParallelismMixIn
from .queue_utils import is_queue_eventually_not_empty
from .queue_utils import SimpleMultiprocessingQueue
from .queue_utils import TestingQueue
from .threading_utils import InfiniteThread


def confirm_parallelism_is_stopped(
    framework: InfiniteLoopingParallelismMixIn,
    timeout_seconds: Optional[Union[float, int]] = None,
) -> None:
    """Confirm that a parallel thread/process is stopped.

    Optionally wait until a timeout has passed before raising the error.

    This is often used during testing when you want to soft_stop a parallel framework and then wait for the soft stop to completely process everything so that you can assert things about what is in the queues.
    And then and empty queues before actually joining the parallel framework to avoid broken pipe errors and hanging on Windows platforms.
    """
    start_time = perf_counter()
    while True:
        if framework.is_stopped():
            return
        if timeout_seconds is None:
            break
        if perf_counter() - start_time >= timeout_seconds:
            break
        sleep(0.2)  # wait in between checking to allow things to run in the background

    raise ParallelFrameworkStillNotStoppedError()


def put_log_message_into_queue(
    log_level_of_this_message: int,
    the_message: Any,
    the_queue: Union[
        Queue[  # pylint: disable=unsubscriptable-object # Eli (3/12/20) not sure why pylint doesn't recognize this type annotation
            Dict[str, Any]
        ],
        SimpleMultiprocessingQueue,
        multiprocessing.queues.Queue[  # pylint: disable=unsubscriptable-object # Eli (3/12/20) not sure why pylint doesn't recognize this type annotation
            Dict[str, Any]
        ],
    ],
    log_level_threshold: int,
    pause_after_put: bool = False,
) -> None:
    """Put a log message into a queue.

    The message is only put in if the log level of the message meets the
    threshold of the queue.
    """
    if log_level_of_this_message >= log_level_threshold:
        comm_dict = {
            "communication_type": "log",
            "log_level": log_level_of_this_message,
            "message": the_message,
        }
        the_queue.put_nowait(comm_dict)
    if not isinstance(the_queue, SimpleMultiprocessingQueue) and pause_after_put:
        is_queue_eventually_not_empty(the_queue)


def invoke_process_run_and_check_errors(
    the_process: InfiniteLoopingParallelismMixIn,
    num_iterations: int = 1,
    perform_setup_before_loop: bool = False,
    perform_teardown_after_loop: bool = False,
) -> None:
    """Call the run method of a process and raise any errors.

    This is often useful in unit testing. This should only be used on
    processes that have not been started.
    """
    the_process.run(
        num_iterations=num_iterations,
        perform_setup_before_loop=perform_setup_before_loop,
        perform_teardown_after_loop=perform_teardown_after_loop,
    )

    error_queue = the_process.get_fatal_error_reporter()
    is_item_in_queue = not error_queue.empty()
    if not isinstance(error_queue, (SimpleMultiprocessingQueue, TestingQueue)):
        is_item_in_queue = is_queue_eventually_not_empty(error_queue)
    if is_item_in_queue:
        err_info = the_process.get_fatal_error_reporter().get_nowait()
        if isinstance(the_process, InfiniteProcess):
            if not isinstance(err_info, tuple):
                raise NotImplementedError("Errors from InfiniteProcess must be Tuple[Exception,str]")
            excp, trace = err_info
            if not isinstance(excp, Exception):
                raise NotImplementedError("Errors from InfiniteProcess must be Tuple[Exception,str]")
            if not isinstance(trace, str):
                raise NotImplementedError("Errors from InfiniteProcess must be Tuple[Exception,str]")
            InfiniteProcess.log_and_raise_error_from_reporter((excp, trace))
        if not isinstance(err_info, Exception):

            raise NotImplementedError("Errors from InfiniteThread must be Exceptions")

        InfiniteThread.log_and_raise_error_from_reporter(err_info)
