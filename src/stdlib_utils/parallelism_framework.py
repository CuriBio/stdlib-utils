# -*- coding: utf-8 -*-
"""Functionality to enhance parallelism."""
from __future__ import annotations

import logging
import multiprocessing
import multiprocessing.queues
import multiprocessing.synchronize
import queue
from statistics import stdev
import threading
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from .constants import NANOSECONDS_PER_CENTIMILLISECOND
from .misc import get_formatted_stack_trace
from .misc import print_exception
from .queue_utils import is_queue_eventually_not_empty
from .queue_utils import SimpleMultiprocessingQueue
from .queue_utils import TestingQueue


def calculate_iteration_time_ns(start_timepoint_of_iteration: int) -> int:
    return time.perf_counter_ns() - start_timepoint_of_iteration


# pylint: disable=too-many-instance-attributes
class InfiniteLoopingParallelismMixIn:
    """Mix-in for infinite looping.

    Attrs:
        num_longest_iterations: the quantity of longest iterations the object should keep track of.

    Args:
        fatal_error_reporter: a queue to report any fatal unhandled errors back to the thread that started this process
        logging_level: what threshold to use for logging events
        stop_event: When set (typically by calling .stop()), this will cause the infinite loop to exit on the next iteration
        soft_stop_event: When set (typically by calling .soft_stop()), this will cause the infinite loop to exit the next iteration that all conditionals indicating a soft_stop is possible are met (typically used to ensure all incoming tasks/queues are empty and there is nothing currently available to process)
        teardown_complete_event: After the infinite loop is exited, the _teardown_after_loop() method will be called. This event can be monitored by the parent thread to determine when the teardown has completed and the process is ready to have any needed additional clean-up performed by the parent before the parent calls .join().
        minimum_iteration_duration_seconds: In order for the process not to unnecessarily consume CPU resources while looping, the loop will sleep at the end of each iteration until this threshold duration is met.
    """

    num_longest_iterations = 5

    def __init__(
        self,
        fatal_error_reporter: Union[
            queue.Queue[str],
            multiprocessing.queues.Queue[Tuple[Exception, str]],
            SimpleMultiprocessingQueue,
            TestingQueue,
        ],
        logging_level: int,
        stop_event: Union[threading.Event, multiprocessing.synchronize.Event],
        soft_stop_event: Union[threading.Event, multiprocessing.synchronize.Event],
        teardown_complete_event: Union[threading.Event, multiprocessing.synchronize.Event],
        start_up_complete_event: Union[threading.Event, multiprocessing.synchronize.Event],
        pause_event: Union[threading.Event, multiprocessing.synchronize.Event],
        minimum_iteration_duration_seconds: Union[float, int] = 0.01,
    ) -> None:
        self._init_time_ns: Optional[int] = None
        self._stop_event = stop_event
        self._soft_stop_event = soft_stop_event
        self._teardown_complete_event = teardown_complete_event
        self._start_up_complete_event = start_up_complete_event
        self._pause_event = pause_event
        self._fatal_error_reporter = fatal_error_reporter
        self._process_can_be_soft_stopped = True
        self._logging_level = logging_level
        self._minimum_iteration_duration_seconds = minimum_iteration_duration_seconds
        self._idle_iteration_time_ns = 0
        self._percent_use_values: List[float] = list()
        self._longest_iterations: List[int] = list()

    def _init_performance_measurements(self) -> None:
        # separate to make mocking easier
        self._reset_performance_measurements()

    def _reset_performance_measurements(self) -> None:
        self._start_timepoint_of_last_performance_measurement = time.perf_counter_ns()
        self._idle_iteration_time_ns = 0

    def _reset_start_time(self) -> None:
        self._init_time_ns = time.perf_counter_ns()

    def get_start_timepoint_of_performance_measurement(self) -> int:
        return self._start_timepoint_of_last_performance_measurement

    def get_elapsed_time_since_last_performance_measurement(self) -> int:
        return time.perf_counter_ns() - self._start_timepoint_of_last_performance_measurement

    def reset_performance_tracker(self) -> Dict[str, Any]:
        """Reset performance tracking and return various metrics."""
        out_dict: Dict[str, Any] = {}
        out_dict["start_timepoint_of_measurements"] = self._start_timepoint_of_last_performance_measurement
        out_dict["idle_iteration_time_ns"] = self._idle_iteration_time_ns
        out_dict["percent_use"] = 100 * (
            1 - self._idle_iteration_time_ns / self.get_elapsed_time_since_last_performance_measurement()
        )
        out_dict["longest_iterations"] = self._longest_iterations
        self._percent_use_values.append(out_dict["percent_use"])
        self._reset_performance_measurements()
        return out_dict

    def get_percent_use_values(self) -> List[float]:
        return self._percent_use_values

    def get_percent_use_metrics(self) -> Dict[str, float]:
        metrics = {
            "max": max(self._percent_use_values),
            "min": min(self._percent_use_values),
            "stdev": round(stdev(self._percent_use_values), 6),
            "mean": round(sum(self._percent_use_values) / len(self._percent_use_values), 6),
        }
        return metrics

    def get_idle_time_ns(self) -> float:
        return self._idle_iteration_time_ns

    def get_minimum_iteration_duration_seconds(self) -> Union[float, int]:
        return self._minimum_iteration_duration_seconds

    def get_cms_since_init(self) -> int:
        if self._init_time_ns is None:
            return 0
        ns_since_init = time.perf_counter_ns() - self._init_time_ns
        return ns_since_init // NANOSECONDS_PER_CENTIMILLISECOND

    def get_logging_level(self) -> int:
        return self._logging_level

    @staticmethod
    def log_and_raise_error_from_reporter(error_info: Exception) -> None:
        err = error_info
        if not isinstance(err, Exception):
            raise NotImplementedError("Error in the code, this should always be an Exception.")
        formatted_traceback = get_formatted_stack_trace(err)
        logging.exception(formatted_traceback)
        raise err

    def get_fatal_error_reporter(
        self,
    ) -> Union[
        queue.Queue[str],
        multiprocessing.queues.Queue[Tuple[Exception, str]],
        SimpleMultiprocessingQueue,
        TestingQueue,
    ]:
        return self._fatal_error_reporter

    def _report_fatal_error(self, the_err: Exception) -> None:
        self._fatal_error_reporter.put_nowait(the_err)  # type: ignore # the subclasses all have an instance of fatal error reporter. there may be a more elegant way to handle this to make mypy happy though... (Eli 2/12/20)

    def _setup_before_loop(self) -> None:
        """Perform any necessary setup prior to initiating the infinite loop.

        This can be overridden by the subclass, but the super method
        should always be called at the start of the subclass's
        implementation.
        """
        self._init_performance_measurements()
        self._reset_start_time()

    def _teardown_after_loop(self) -> None:
        """Perform any necessary teardown after the infinite loop has exited.

        It's the responsibility of this method and parent process to make sure all queues get emptied before join is called.

        This can be overridden by the subclass, but the super method should always be called at the end of the subclass's implementation.
        """
        if not hasattr(self, "_teardown_complete_event"):
            raise NotImplementedError(
                "Classes using this mixin must have a _teardown_complete_event attribute."
            )
        teardown_complete_event = getattr(self, "_teardown_complete_event")

        teardown_complete_event.set()

    def run(
        self,
        num_iterations: Optional[int] = None,
        perform_setup_before_loop: bool = True,
        perform_teardown_after_loop: bool = True,
    ) -> None:
        """Run the thread.

        Args:
            num_iterations: typically used for unit testing to just execute one or a few cycles. if left as None will loop infinitely
            perform_setup_before_loop: this can be disabled when needed during unit testing
            perform_teardown_after_loop: this can be disabled when needed during unit testing

        This sets up the basic flow control and error handling for the thread.
        Subclasses should implement functionality to be executed during each
        cycle in the _commands_for_each_run_iteration method.
        """
        if num_iterations is None:
            num_iterations = -1
        completed_iterations = 0
        if perform_setup_before_loop:
            try:
                self._setup_before_loop()
            except Exception as e:  # pylint: disable=broad-except # The deliberate goal of this is to catch everything and put it into the error queue
                print_exception(e, "cf477f32-9797-417e-a157-ea6e0c4f25d1")
                self._report_fatal_error(e)
                return
        self._start_up_complete_event.set()
        while True:
            start_timepoint_of_iteration = time.perf_counter_ns()
            self._process_can_be_soft_stopped = True
            if not self._pause_event.is_set():
                try:
                    self._commands_for_each_run_iteration()
                except Exception as e:  # pylint: disable=broad-except # The deliberate goal of this is to catch everything and put it into the error queue
                    print_exception(e, "88a25177-b2a1-4bbb-ba92-bf5810594a99")
                    self._report_fatal_error(e)
                    self.stop()
            if self.is_preparing_for_soft_stop() and self._process_can_be_soft_stopped:
                self.stop()

            if self.is_stopped():
                # Having the check for is_stopped after the first iteration of run allows easier unit testing.
                break
            completed_iterations += 1
            if completed_iterations == num_iterations:
                break
            # only decide to sleep if there are more iterations to do. this will keep unit tests executing more quickly
            self._sleep_for_idle_time_during_iteration(start_timepoint_of_iteration)
        if perform_teardown_after_loop:
            try:
                self._teardown_after_loop()
            except Exception as e:  # pylint: disable=broad-except # The deliberate goal of this is to catch everything and put it into the error queue
                print_exception(e, "bd9a8587-e79b-43cb-8ffe-0bf45740599d")
                self._report_fatal_error(e)

    def _sleep_for_idle_time_during_iteration(self, start_timepoint_of_iteration: int) -> None:
        iteration_time_ns = calculate_iteration_time_ns(start_timepoint_of_iteration)

        longest_iterations = self._longest_iterations
        if len(longest_iterations) < 5:
            longest_iterations.append(iteration_time_ns)
        else:
            min_longest_iteration = min(longest_iterations)
            if iteration_time_ns > min_longest_iteration:
                longest_iterations[longest_iterations.index(min_longest_iteration)] = iteration_time_ns

        idle_time_ns = int(self.get_minimum_iteration_duration_seconds() * 10 ** 9) - iteration_time_ns
        if idle_time_ns > 0:
            self._idle_iteration_time_ns += idle_time_ns
            time.sleep(idle_time_ns / 10 ** 9)

    def _commands_for_each_run_iteration(self) -> None:
        """Execute additional commands inside the run loop."""

    def stop(self) -> None:
        """Trigger the infinite loop to break on next iteration.

        This will leave any unprocessed tasks still in incoming queues, which must be emptied before the process can be joined.

        It's the responsibility of _teardown_after_loop and parent
        process to make sure all queues get emptied before join is
        called.
        """
        if not hasattr(self, "_stop_event"):
            raise NotImplementedError("Classes using this mixin must have a _stop_event attribute.")
        stop_event = getattr(self, "_stop_event")

        stop_event.set()

    def soft_stop(self) -> None:
        """Stop the infinite loop when the process indicates it is OK to do so.

        Typically useful for unit testing. For example waiting until all
        queued up items have been handled.

        It's the responsibility of _teardown_after_loop and parent process to make sure all queues get emptied before join is called.
        """
        if not hasattr(self, "_soft_stop_event"):
            raise NotImplementedError("Classes using this mixin must have a _soft_stop_event attribute.")
        soft_stop_event = getattr(self, "_soft_stop_event")

        soft_stop_event.set()

    def hard_stop(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Stop the infinite loop and drain all queues.

        Timeout can be specified (in seconds) which will override waiting for process to tear itself down.

        Items in queues will be returned in a dict
        """
        self.stop()
        self._teardown_after_loop()
        start_timepoint = time.perf_counter()
        while True:
            if timeout is not None:
                elapsed_time = time.perf_counter() - start_timepoint
                if elapsed_time > timeout:
                    break
            if self.is_teardown_complete():
                break

        item_dict = self._drain_all_queues()

        error_queue = self.get_fatal_error_reporter()
        error_items = list()
        if isinstance(error_queue, (SimpleMultiprocessingQueue, TestingQueue)):
            while not error_queue.empty():
                error_items.append(error_queue.get_nowait())
        else:
            while is_queue_eventually_not_empty(error_queue):
                error_items.append(error_queue.get_nowait())

        item_dict["fatal_error_reporter"] = error_items
        return item_dict

    def _drain_all_queues(self) -> Dict[str, Any]:
        """Drain all queues of the process except the fatal_error_reporter.

        fatal_error_reporter will always be drained by hard_stop.

        This method should be overriden by subclasses implementations
        """
        # pylint:disable=no-self-use # Tanner (5/12/20): this is needed so method signature matches subclass implementation
        return dict()

    def is_start_up_complete(self) -> bool:
        """Check if the parallel instance has completed start up."""
        if not hasattr(self, "_start_up_complete_event"):
            raise NotImplementedError(
                "Classes using this mixin must have a _start_up_complete_event attribute."
            )
        start_up_complete_event = getattr(self, "_start_up_complete_event")

        is_set = start_up_complete_event.is_set()
        if not isinstance(is_set, bool):
            raise NotImplementedError("The return value from this should always be a bool.")
        return is_set

    def is_stopped(self) -> bool:
        """Check if the parallel instance is stopped."""
        if not hasattr(self, "_stop_event"):
            raise NotImplementedError("Classes using this mixin must have a _stop_event attribute.")
        stop_event = getattr(self, "_stop_event")

        is_set = stop_event.is_set()
        if not isinstance(is_set, bool):
            raise NotImplementedError("The return value from this should always be a bool.")
        return is_set

    def is_preparing_for_soft_stop(self) -> bool:
        """Check if the parallel instance is preparing to soft stop."""
        if not hasattr(self, "_soft_stop_event"):
            raise NotImplementedError("Classes using this mixin must have a _soft_stop_event attribute.")
        soft_stop_event = getattr(self, "_soft_stop_event")
        if not isinstance(soft_stop_event, (threading.Event, multiprocessing.synchronize.Event)):
            raise NotImplementedError(
                "Classes using this mixin must have a _soft_stop_event as either a threading.Event or multiprocessing.Event"
            )
        return soft_stop_event.is_set()

    def is_teardown_complete(self) -> bool:
        """Check if the parallel instance has completed tearing itself down."""
        if not hasattr(self, "_teardown_complete_event"):
            raise NotImplementedError(
                "Classes using this mixin must have a _teardown_complete_event attribute."
            )
        teardown_complete_event = getattr(self, "_teardown_complete_event")
        if not isinstance(
            teardown_complete_event,
            (threading.Event, multiprocessing.synchronize.Event),
        ):
            raise NotImplementedError(
                "Classes using this mixin must have a _teardown_complete_event as either a threading.Event or multiprocessing.Event"
            )
        return teardown_complete_event.is_set()

    def pause(self) -> None:
        """Have the infinite loop skip executing commands.

        This is typically useful during integration testing scenarios.
        """
        if not hasattr(self, "_pause_event"):
            raise NotImplementedError("Classes using this mixin must have a _pause_event attribute.")
        pause_event = getattr(self, "_pause_event")

        pause_event.set()

    def resume(self) -> None:
        """Have the infinite loop resume executing commands.

        This is typically useful during integration testing scenarios.
        """
        if not hasattr(self, "_pause_event"):
            raise NotImplementedError("Classes using this mixin must have a _pause_event attribute.")
        pause_event = getattr(self, "_pause_event")

        pause_event.clear()

    def is_paused(self) -> bool:
        """Check if framework is paused."""
        if not hasattr(self, "_pause_event"):
            raise NotImplementedError("Classes using this mixin must have a _pause_event attribute.")
        pause_event = getattr(self, "_pause_event")
        if not isinstance(pause_event, (threading.Event, multiprocessing.synchronize.Event)):
            raise NotImplementedError(
                "Classes using this mixin must have a _pause_event as either a threading.Event or multiprocessing.Event"
            )
        return pause_event.is_set()
