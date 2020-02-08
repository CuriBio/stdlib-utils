# -*- coding: utf-8 -*-
"""Controlling communication with the OpalKelly FPGA Boards."""
import logging
import multiprocessing
from multiprocessing import Event
from multiprocessing import Process
import multiprocessing.queues
import queue
import traceback
from typing import Optional


class SimpleMultiprocessingQueue(multiprocessing.queues.SimpleQueue):
    """Some additional basic functionality.

    Since SimpleQueue is not technically a class, there are some tricks to subclassing it: https://stackoverflow.com/questions/39496554/cannot-subclass-multiprocessing-queue-in-python-3-5
    """

    def __init__(self):
        ctx = multiprocessing.get_context()
        super().__init__(ctx=ctx)

    def get_nowait(self):
        """Get value or raise error if empty."""
        if self.empty():
            raise queue.Empty()
        return self.get()


class GenericProcess(Process):
    """Process with some enhanced functionality.

    Because of the more explict error reporting/handling during the run method, the Process.exitcode value will still be 0 when the process exits after handling an error.

    Args:
        fatal_error_reporter: set up as a queue to be thread/process safe. If any error is unhandled during run, it is fed into this queue so that calling thread can know the full details about the problem in this process.
    """

    def __init__(self, fatal_error_reporter: SimpleMultiprocessingQueue):
        super().__init__()
        self._stop_event = Event()
        self._fatal_error_reporter = fatal_error_reporter
        self.process_can_be_soft_stopped = True
        self._soft_stop_event = Event()

    def get_fatal_error_reporter(self) -> SimpleMultiprocessingQueue:
        return self._fatal_error_reporter

    def run(self, num_iterations: Optional[int] = None):
        """Run the process.

        Args:
            num_iterations: typically used for unit testing to just execute one or a few cycles. if left as None will loop infinitely
            run_once: typically used for unit testing to just execute one cycle

        This sets up the basic flow control and error handling.
        Subclasses should implement functionality to be executed each
        cycle in the _commands_for_each_run_iteration method.
        """
        # pylint: disable=arguments-differ
        if num_iterations is None:
            num_iterations = -1
        completed_iterations = 0
        while True:
            self.process_can_be_soft_stopped = True
            try:
                self._commands_for_each_run_iteration()
            except Exception as e:  # pylint: disable=broad-except # The deliberate goal of this is to catch everything and put it into the error queue

                # format the stack trace (Eli 2/7/20 couldn't figure out a way to get the stack trace from the exception itself once it had passed back into the main process, so need to grab it explicitly here) https://stackoverflow.com/questions/4564559/get-exception-description-and-stack-trace-which-caused-an-exception-all-as-a-st
                stack = traceback.extract_stack()[:-3] + traceback.extract_tb(
                    e.__traceback__
                )  # add limit=??
                pretty = traceback.format_list(stack)
                formatted_stack_trace = "".join(pretty) + "\n  {} {}".format(
                    e.__class__, e
                )

                self._fatal_error_reporter.put((e, formatted_stack_trace))
                self.stop()
            if self.is_preparing_for_soft_stop() and self.process_can_be_soft_stopped:
                self.stop()

            if self.is_stopped():
                # Having the check for is_stopped after the first iteration of run allows easier unit testing.
                break
            completed_iterations += 1
            if completed_iterations == num_iterations:
                break

    def _commands_for_each_run_iteration(self):
        """Execute additional commands inside the run loop."""

    def stop(self):
        """Safely stops the process."""
        self._stop_event.set()

    def soft_stop(self):
        """Stop the process when the process indicates it is OK to do so.

        Typically useful for unit testing. For example waiting until all
        queued up items have been handled.
        """
        self._soft_stop_event.set()

    def is_stopped(self):
        return self._stop_event.is_set()

    def is_preparing_for_soft_stop(self):
        return self._soft_stop_event.is_set()


def invoke_process_run_and_check_errors(
    the_process: GenericProcess, num_iterations: int = 1
):
    """Call the run method of a process and raise any errors.

    This is often useful in unit testing. This should only be used on
    processes that have not been started.
    """
    the_process.run(num_iterations=num_iterations)
    try:
        err, formatted_traceback = the_process.get_fatal_error_reporter().get_nowait()
        logging.exception(formatted_traceback)
        raise err
    except queue.Empty:
        pass
