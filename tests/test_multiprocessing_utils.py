# -*- coding: utf-8 -*-
import logging
import multiprocessing
from multiprocessing import Process
import queue
import time

import pytest
from stdlib_utils import BadQueueTypeError
from stdlib_utils import InfiniteLoopingParallelismMixIn
from stdlib_utils import InfiniteProcess
from stdlib_utils import invoke_process_run_and_check_errors
from stdlib_utils import SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE
from stdlib_utils import SimpleMultiprocessingQueue
from stdlib_utils import TestingQueue

from .fixtures_parallelism import InfiniteProcessThatCannotBeSoftStopped
from .fixtures_parallelism import InfiniteProcessThatCountsIterations
from .fixtures_parallelism import InfiniteProcessThatRaisesError
from .fixtures_parallelism import InfiniteProcessThatRaisesErrorInSetup
from .fixtures_parallelism import InfiniteProcessThatRaisesErrorInTeardown
from .fixtures_parallelism import InfiniteProcessThatTracksSetup
from .fixtures_parallelism import init_test_args_InfiniteLoopingParallelismMixIn

# adapted from https://stackoverflow.com/questions/21611559/assert-that-a-method-was-called-with-one-argument-out-of-several
# ...but does not seem to be working as expected
# def MockAny(cls):
#     class MockAny(cls):
#         def __eq__(self, other):
#             return isinstance(other, cls)

#     return MockAny()


class InfiniteProcessThatPopulatesQueue(InfiniteProcess):
    def __init__(self, queue_to_populate, fatal_error_reporter) -> None:
        super().__init__(fatal_error_reporter)
        self._queue_to_populate = queue_to_populate
        self._counter = 0

    def _commands_for_each_run_iteration(self):
        self._queue_to_populate.put(self._counter)
        self._counter += 1
        time.sleep(0.05)


def test_InfiniteProcess_super_Process_is_called_during_init(mocker):
    mocked_init = mocker.patch.object(Process, "__init__")
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcess(error_queue)
    mocked_init.assert_called_once_with(p)


def test_InfiniteProcess_super_InfiniteLoopingParallelismMixIn_is_called_during_init(
    mocker,
):
    mocked_init = mocker.patch.object(InfiniteLoopingParallelismMixIn, "__init__")
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcess(error_queue)
    # mocked_init.assert_called_once_with(p, error_queue, logging.INFO,MockAny(multiprocessing.Event),MockAny(multiprocessing.Event))
    mocked_init.assert_called_once_with(
        p,
        error_queue,
        *init_test_args_InfiniteLoopingParallelismMixIn,
        minimum_iteration_duration_seconds=0.01,
    )


def test_InfiniteProcess_can_set_minimum_iteration_duration():

    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcess(error_queue, minimum_iteration_duration_seconds=0.22)

    assert p.get_minimum_iteration_duration_seconds() == 0.22


def test_InfiniteProcess_internal_logging_level_can_be_set():

    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcess(error_queue, logging_level=logging.DEBUG)
    assert p.get_logging_level() == logging.DEBUG


def test_InfiniteProcess_can_be_run_and_stopped():
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcess(error_queue)
    p.start()
    assert p.is_alive() is True
    p.stop()
    p.join()
    assert p.is_alive() is False
    assert p.exitcode == 0


@pytest.mark.timeout(4)  # set a timeout because the test can hang as a failure mode
def test_InfiniteProcess_can_be_run_and_soft_stopped():
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcess(error_queue)
    p.start()
    assert p.is_alive() is True
    p.soft_stop()
    p.join()
    assert p.is_alive() is False
    assert p.exitcode == 0


def test_InfiniteProcess__will_not_soft_stop_when_told_not_to():
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatCannotBeSoftStopped(error_queue)
    p.soft_stop()
    p.run(num_iterations=1)
    assert p.is_stopped() is False


@pytest.mark.timeout(2)  # set a timeout because the test can hang as a failure mode
def test_InfiniteProcess__run_can_be_executed_just_once(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcess(error_queue)
    spied_is_stopped = mocker.spy(p, "is_stopped")
    p.run(num_iterations=1)
    spied_is_stopped.assert_called_once()


@pytest.mark.timeout(2)  # set a timeout because the test can hang as a failure mode
def test_InfiniteProcess__run_can_be_executed_just_four_cycles(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcess(error_queue)
    spied_is_stopped = mocker.spy(p, "is_stopped")
    p.run(num_iterations=4)
    assert spied_is_stopped.call_count == 4


def test_InfiniteProcess_run_calls___commands_for_each_run_iteration(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatCountsIterations(error_queue)
    mocker.patch.object(p, "is_stopped", autospec=True, return_value=True)
    p.run()
    assert p.get_num_iterations() == 1


def test_InfiniteProcess__queue_is_populated_with_error_occuring_during_run__and_stop_is_called(
    mocker,
):
    expected_error = ValueError("test message")
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatRaisesError(error_queue)
    mocker.patch("builtins.print", autospec=True)  # don't print the error message to stdout
    spied_stop = mocker.spy(p, "stop")

    p.run()
    assert error_queue.empty() is False
    assert spied_stop.call_count == 1
    actual_error, _ = error_queue.get()
    assert isinstance(actual_error, type(expected_error))
    assert str(actual_error) == str(expected_error)
    # assert actual_error == expected_error # Eli (12/24/19): for some reason this asserting doesn't pass...not sure why....so testing class type and str instead


def test_InfiniteProcess__queue_is_populated_with_error_occuring_during_live_spawned_run(
    mocker,
):
    # spied_print_exception = mocker.spy(
    #     parallelism_framework, "print_exception"
    # )  # Eli (3/13/20) can't figure out why this isn't working (call count never gets to 1), so just asserting about print instead
    mocker.patch("builtins.print", autospec=True)  # don't print the error message to stdout
    expected_error = ValueError("test message")
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatRaisesError(error_queue)
    p.start()
    p.join()
    assert error_queue.empty() is False
    actual_error, actual_stack_trace = error_queue.get()
    # assert spied_print_exception.call_count == 1
    # assert mocked_print.call_count==1

    assert isinstance(actual_error, type(expected_error))
    assert str(actual_error) == str(expected_error)
    assert p.exitcode == 0  # When errors are handled, the error code is 0
    # assert actual_error == expected_error # Eli (12/24/19): for some reason this asserting doesn't pass...not sure why....so testing class type and str instead
    assert 'raise ValueError("test message")' in actual_stack_trace


def test_InfiniteProcess__error_queue_is_populated_when_error_queue_is_multiprocessing_Queue(
    mocker,
):
    mocker.patch("builtins.print")  # don't print the error message to stdout
    error_queue = multiprocessing.Queue()
    p = InfiniteProcessThatRaisesError(error_queue)
    with pytest.raises(ValueError, match="test message"):
        invoke_process_run_and_check_errors(p)


def test_InfiniteProcess__calls_setup_before_loop(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatTracksSetup(error_queue)
    p.run(num_iterations=1)
    assert error_queue.empty() is True
    assert p.is_setup() is True


def test_InfiniteProcess__catches_error_in_setup_before_loop_and_does_not_run_iteration_or_teardown(
    mocker,
):
    expected_error = ValueError("error during setup")
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatRaisesErrorInSetup(error_queue)
    mocker.patch("builtins.print", autospec=True)  # don't print the error message to stdout
    p.run(num_iterations=1)
    assert error_queue.empty() is False
    actual_error, _ = error_queue.get_nowait()
    assert p.get_num_iterations() == 0
    assert p.is_teardown_complete() is False
    assert isinstance(actual_error, type(expected_error))
    assert str(actual_error) == str(expected_error)


def test_InfiniteProcess__calls_teardown_after_loop(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcess(error_queue)
    p.run(num_iterations=1)
    assert error_queue.empty() is True
    assert p.is_teardown_complete() is True


def test_InfiniteProcess__catches_error_in_teardown_after_loop(mocker):
    expected_error = ValueError("error during teardown")
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatRaisesErrorInTeardown(error_queue)
    mocker.patch("builtins.print", autospec=True)  # don't print the error message to stdout
    p.run(num_iterations=1)
    assert error_queue.empty() is False
    actual_error, _ = error_queue.get_nowait()
    assert isinstance(actual_error, type(expected_error))
    assert str(actual_error) == str(expected_error)


@pytest.mark.timeout(
    45
)  # Eli (2/10/21): Because there can be ~40 items put into the queue, need to ensure sufficient time to pull them all out using the sleep time between polling the queue
@pytest.mark.slow
def test_InfiniteProcess__pause_and_resume_work_while_running():
    test_queue = SimpleMultiprocessingQueue()
    error_queue = multiprocessing.Queue()
    p = InfiniteProcessThatPopulatesQueue(test_queue, error_queue)
    p.start()
    seconds_to_sleep_while_queue_populating = 2  # Eli (12/14/20): in GitHub Windows containers, 0.05 seconds was too short, so just bumping up to 1 second # Tanner (1/31/21): bumping to 2 seconds after another CI issue
    time.sleep(seconds_to_sleep_while_queue_populating)  # let the queue populate
    p.pause()
    items_in_queue_at_pause = []
    while test_queue.empty() is False:
        items_in_queue_at_pause.append(test_queue.get())
        time.sleep(
            SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE
        )  # don't relentlessly poll the queue # Eli (2/10/21): There was an odd hanging that occurred once during CI in a windows container...possibly due to relentlessly checking empty/get of the queue(?) https://github.com/CuriBio/stdlib-utils/pull/87/checks?check_run_id=1856410303

    assert len(items_in_queue_at_pause) > 0
    last_item_in_queue_at_pause = items_in_queue_at_pause[-1]

    time.sleep(
        seconds_to_sleep_while_queue_populating
    )  # give the queue time to populate if pause was unsuccessful
    assert test_queue.empty() is True

    p.resume()
    time.sleep(seconds_to_sleep_while_queue_populating)  # give the queue time to populate
    hard_stop_results = p.hard_stop()
    p.join()

    assert len(hard_stop_results["fatal_error_reporter"]) == 0

    items_in_queue_at_stop = []
    while test_queue.empty() is False:
        items_in_queue_at_stop.append(test_queue.get())
        time.sleep(
            SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE
        )  # don't relentlessly poll the queue # Eli (2/10/21): There was an odd hanging that occurred once during CI in a windows container...possibly due to relentlessly checking empty/get of the queue(?) https://github.com/CuriBio/stdlib-utils/pull/87/checks?check_run_id=1856410303

    assert len(items_in_queue_at_stop) > 0
    assert items_in_queue_at_stop[0] - 1 == last_item_in_queue_at_pause


def test_InfiniteProcess_start__raises_error_if_error_queue_is_incorrect_queue_type():
    error_queue1 = TestingQueue()
    p1 = InfiniteProcess(error_queue1)
    with pytest.raises(
        BadQueueTypeError,
        match=f"_fatal_error_reporter must be a SimpleMultiprocessingQueue or multiprocessing.queues.Queue if starting this process, not {type(error_queue1)}",
    ):
        p1.start()

    error_queue2 = queue.Queue()
    p2 = InfiniteProcess(error_queue2)
    with pytest.raises(
        BadQueueTypeError,
        match=f"_fatal_error_reporter must be a SimpleMultiprocessingQueue or multiprocessing.queues.Queue if starting this process, not {type(error_queue2)}",
    ):
        p2.start()
