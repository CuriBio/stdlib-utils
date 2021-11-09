# -*- coding: utf-8 -*-
import logging
import multiprocessing
import queue
import time

import pytest
from stdlib_utils import confirm_parallelism_is_stopped
from stdlib_utils import InfiniteProcess
from stdlib_utils import InfiniteThread
from stdlib_utils import invoke_process_run_and_check_errors
from stdlib_utils import ParallelFrameworkStillNotStoppedError
from stdlib_utils import parallelism_utils
from stdlib_utils import put_log_message_into_queue
from stdlib_utils import SimpleMultiprocessingQueue

from .fixtures_parallelism import InfiniteProcessThatCountsIterations
from .fixtures_parallelism import InfiniteProcessThatRaisesError
from .fixtures_parallelism import InfiniteProcessThatTracksSetup
from .fixtures_parallelism import InfiniteThreadThatRaisesError


def test_invoke_process_run_and_check_errors__passes_values_for_InfiniteProcess(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatCountsIterations(error_queue)
    invoke_process_run_and_check_errors(p)  # runs once by default
    assert p.get_num_iterations() == 1

    invoke_process_run_and_check_errors(p, num_iterations=2)
    assert p.get_num_iterations() == 3


def test_invoke_process_run_and_check_errors__pauses_long_enough_to_process_standard_multiprocessing_queue(
    mocker,
):
    error_queue = multiprocessing.Queue()
    p = InfiniteProcessThatRaisesError(error_queue)
    mocker.patch("builtins.print", autospec=True)  # don't print the error message to stdout
    with pytest.raises(ValueError, match="test message"):
        invoke_process_run_and_check_errors(p)


def test_invoke_process_run_and_check_errors__raises_and_logs_error_for_InfiniteProcess(
    mocker,
):
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatRaisesError(error_queue)
    mocked_log = mocker.patch.object(logging, "exception", autospec=True)
    mocker.patch("builtins.print", autospec=True)  # don't print the error message to stdout
    with pytest.raises(ValueError, match="test message"):
        invoke_process_run_and_check_errors(p)
    assert error_queue.empty() is True  # the error should have been popped off the queu
    assert mocked_log.call_count == 1


def test_invoke_process_run_and_check_errors__does_not_run_setup_or_teardown_by_default():
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatTracksSetup(error_queue)
    invoke_process_run_and_check_errors(p)  # runs once by default
    assert p.get_num_iterations() == 1
    assert p.is_setup() is False
    assert p.is_teardown_complete() is False

    invoke_process_run_and_check_errors(p, num_iterations=2)
    assert p.get_num_iterations() == 3


def test_invoke_process_run_and_check_errors__runs_setup_with_given_kwarg():
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatTracksSetup(error_queue)
    invoke_process_run_and_check_errors(p, perform_setup_before_loop=True)  # runs once by default
    assert p.get_num_iterations() == 1
    assert p.is_setup() is True


def test_invoke_process_run_and_check_errors__runs_teardown_with_given_kwarg():
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatTracksSetup(error_queue)
    invoke_process_run_and_check_errors(p, perform_teardown_after_loop=True)  # runs once by default
    assert p.get_num_iterations() == 1
    assert p.is_teardown_complete() is True


def test_invoke_process_run_and_check_errors__raises_and_logs_error_for_InfiniteThread(
    mocker,
):
    error_queue = queue.Queue()
    p = InfiniteThreadThatRaisesError(error_queue)
    mocked_log = mocker.patch.object(logging, "exception", autospec=True)
    mocker.patch("builtins.print", autospec=True)  # don't print the error message to stdout
    with pytest.raises(ValueError, match="test message"):
        invoke_process_run_and_check_errors(p)
    assert error_queue.empty() is True  # the error should have been popped off the queue
    assert mocked_log.call_count == 1


def test_put_log_message_into_queue__puts_message_in_when_at_threshold():
    q = queue.Queue()
    msg = "hey"
    put_log_message_into_queue(logging.INFO, msg, q, logging.INFO)
    the_comm = q.get_nowait()
    assert isinstance(the_comm, dict)
    assert the_comm["communication_type"] == "log"
    assert the_comm["log_level"] == logging.INFO
    assert the_comm["message"] == msg


def test_put_log_message_into_queue__puts_message_in_when_above_threshold():
    q = queue.Queue()
    msg = "hey jude"
    put_log_message_into_queue(logging.ERROR, msg, q, logging.WARNING)
    the_comm = q.get_nowait()
    assert the_comm["message"] == msg
    assert the_comm["log_level"] == logging.ERROR


def test_put_log_message_into_queue__does_not_put_message_in_when_below_threshold():
    q = queue.Queue()
    msg = "hey there"
    put_log_message_into_queue(logging.DEBUG, msg, q, logging.INFO)
    assert q.empty() is True


def test_put_log_message_into_queue__sleeps_after_putting_message_into_regular_queue(
    mocker,
):
    spied_is_queue_eventually_not_empty = mocker.spy(parallelism_utils, "is_queue_eventually_not_empty")
    q = queue.Queue()
    msg = "hey there"
    put_log_message_into_queue(
        logging.ERROR,
        msg,
        q,
        logging.WARNING,
        pause_after_put=True,
    )
    spied_is_queue_eventually_not_empty.assert_called_once_with(q)


def test_put_log_message_into_queue__does_not_sleep_after_putting_message_into_simplequeue(
    mocker,
):
    spied_sleep = mocker.spy(time, "sleep")
    sq = SimpleMultiprocessingQueue()
    msg = "hey there"
    put_log_message_into_queue(
        logging.ERROR,
        msg,
        sq,
        logging.WARNING,
        pause_after_put=True,
    )
    spied_sleep.assert_not_called()


def test_put_log_message_into_queue__does_not_sleep_with_default_pause_value_and_regular_queue(
    mocker,
):
    spied_sleep = mocker.spy(time, "sleep")
    q = queue.Queue()
    msg = "hey there"
    put_log_message_into_queue(logging.ERROR, msg, q, logging.WARNING)
    spied_sleep.assert_not_called()


@pytest.mark.parametrize(
    ",".join(("test_framework", "test_description")),
    [
        (InfiniteThread(queue.Queue()), "InfiniteThread"),
        (InfiniteProcess(multiprocessing.Queue()), "InfiniteProcess"),
    ],
)
def test_confirm_parallelism_is_stopped__does_not_wait_if_framework_already_stopped__even_when_timeout_supplied(
    test_framework, test_description, mocker
):
    spied_sleep = mocker.spy(parallelism_utils, "sleep")
    test_framework.stop()
    confirm_parallelism_is_stopped(test_framework, timeout_seconds=10)
    assert spied_sleep.call_count == 0


@pytest.mark.parametrize(
    ",".join(("test_framework", "test_description")),
    [
        (InfiniteThread(queue.Queue()), "InfiniteThread"),
        (InfiniteProcess(multiprocessing.Queue()), "InfiniteProcess"),
    ],
)
def test_confirm_parallelism_is_stopped__raises_error_if_not_stopped(
    test_framework, test_description, mocker
):
    mocker.patch.object(parallelism_utils, "sleep", autospec=True)  # patch sleep to speed up test
    with pytest.raises(ParallelFrameworkStillNotStoppedError):
        confirm_parallelism_is_stopped(test_framework)


@pytest.mark.parametrize(
    ",".join(("test_framework", "test_description")),
    [
        (InfiniteThread(queue.Queue()), "InfiniteThread"),
        (InfiniteProcess(multiprocessing.Queue()), "InfiniteProcess"),
    ],
)
def test_confirm_parallelism_is_stopped__raises_error_if_not_stopped_after_timeout(
    test_framework, test_description, mocker
):
    mocked_sleep = mocker.patch.object(
        parallelism_utils, "sleep", autospec=True
    )  # patch sleep to speed up test
    mocker.patch.object(parallelism_utils, "perf_counter", autospec=True, side_effect=[0, 1, 2, 12])
    with pytest.raises(ParallelFrameworkStillNotStoppedError):
        confirm_parallelism_is_stopped(test_framework, timeout_seconds=10)

    assert mocked_sleep.call_count == 2  # confirm that it did sleep in between checking


@pytest.mark.parametrize(
    ",".join(("test_framework", "test_description")),
    [
        (InfiniteThread(queue.Queue()), "InfiniteThread"),
        (InfiniteProcess(multiprocessing.Queue()), "InfiniteProcess"),
    ],
)
def test_confirm_parallelism_is_stopped__successfully_returns_if_framework_becomes_stopped_during_execution(
    test_framework, test_description, mocker
):
    mocked_sleep = mocker.patch.object(
        parallelism_utils, "sleep", autospec=True
    )  # patch sleep to speed up test
    mocker.patch.object(test_framework, "is_stopped", autospec=True, side_effect=[False, False, True])
    confirm_parallelism_is_stopped(test_framework, timeout_seconds=10)

    assert mocked_sleep.call_count == 2  # confirm that it did sleep in between checking
