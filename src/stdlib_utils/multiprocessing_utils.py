# -*- coding: utf-8 -*-
"""Utilities for multiprocessing."""
from __future__ import annotations

import logging
import multiprocessing
from multiprocessing import Event
from multiprocessing import Process
import multiprocessing.queues
from typing import Any
from typing import Optional
from typing import Tuple
from typing import Union

from .misc import get_formatted_stack_trace
from .parallelism_framework import InfiniteLoopingParallelismMixIn
from .queue_utils import SimpleMultiprocessingQueue
from .queue_utils import TestingQueue


# pylint: disable=duplicate-code
class InfiniteProcess(InfiniteLoopingParallelismMixIn, Process):
    """Process with some enhanced functionality.

    Because of the more explict error reporting/handling during the run method, the Process.exitcode value will still be 0 when the process exits after handling an error.

    Args:
        fatal_error_reporter: set up as a queue to be thread/process safe. If any error is unhandled during run, it is fed into this queue so that calling thread can know the full details about the problem in this process.
    """

    # pylint: disable=duplicate-code

    def __init__(
        self,
        fatal_error_reporter: Union[
            SimpleMultiprocessingQueue,
            multiprocessing.queues.Queue[  # pylint: disable=unsubscriptable-object # Eli (3/12/20) not sure why pylint doesn't recognize this type annotation
                Any
            ],
        ],
        logging_level: int = logging.INFO,
        minimum_iteration_duration_seconds: Union[float, int] = 0.01,
    ) -> None:
        Process.__init__(self)
        InfiniteLoopingParallelismMixIn.__init__(
            self,
            fatal_error_reporter,
            logging_level,
            Event(),
            Event(),
            Event(),
            Event(),
            Event(),
            minimum_iteration_duration_seconds=minimum_iteration_duration_seconds,
        )

    def _report_fatal_error(self, the_err: Exception) -> None:
        formatted_stack_trace = get_formatted_stack_trace(the_err)
        reporter = self._fatal_error_reporter
        if not isinstance(
            reporter,
            (SimpleMultiprocessingQueue, multiprocessing.queues.Queue, TestingQueue),
        ):
            raise NotImplementedError(
                "The error reporter for InfiniteProcess must by a SimpleMultiprocessingQueue or multiprocessing.Queue"
            )
        reporter.put_nowait((the_err, formatted_stack_trace))

    # pylint: disable=duplicate-code # pylint is freaking out and requiring the method to be redefined
    def run(  # pylint: disable=duplicate-code # pylint is freaking out and requiring the method to be redefined
        self,
        num_iterations: Optional[  # pylint: disable=duplicate-code # pylint is freaking out and requiring the method to be redefined
            int  # pylint: disable=duplicate-code # pylint is freaking out and requiring the method to be redefined
        ] = None,
        perform_setup_before_loop: bool = True,
        perform_teardown_after_loop: bool = True,  # pylint: disable=duplicate-code
    ) -> None:
        # For some reason pylint freaks out if this method is only defined in the MixIn https://github.com/PyCQA/pylint/issues/1233
        # pylint: disable=duplicate-code # pylint is freaking out and requiring the method to be redefined
        super().run(
            num_iterations=num_iterations,
            perform_setup_before_loop=perform_setup_before_loop,  # pylint: disable=duplicate-code
            perform_teardown_after_loop=perform_teardown_after_loop,
        )

    @staticmethod
    def log_and_raise_error_from_reporter(error_info: Tuple[Exception, str]) -> None:  # type: ignore[override] # noqa: F821 # we are not calling the super function here, we are completely overriding the type of object it accepts
        err, formatted_traceback = error_info
        logging.exception(formatted_traceback)
        raise err
