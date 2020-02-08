# -*- coding: utf-8 -*-
import logging
from multiprocessing import Process
import queue

import pytest
from stdlib_utils import GenericProcess
from stdlib_utils import invoke_process_run_and_check_errors
from stdlib_utils import SimpleMultiprocessingQueue


def test_SimpleMultiprocessingQueue__get_nowait__returns_value_if_present():
    test_queue = SimpleMultiprocessingQueue()
    expected = "blah"
    test_queue.put(expected)
    actual = test_queue.get_nowait()
    assert actual == expected


@pytest.mark.timeout(0.1)  # set a timeout because the test can hang as a failure mode
def test_SimpleMultiprocessingQueue__get_nowait__raises_error_if_empty():
    test_queue = SimpleMultiprocessingQueue()
    with pytest.raises(queue.Empty):
        test_queue.get_nowait()


def test_GenericProcess_super_is_called_during_init(mocker):
    mocked_init = mocker.patch.object(Process, "__init__")
    error_queue = SimpleMultiprocessingQueue()
    GenericProcess(error_queue)
    mocked_init.assert_called_once_with()


def test_GenericProcess_can_be_run_and_stopped():
    error_queue = SimpleMultiprocessingQueue()
    p = GenericProcess(error_queue)
    p.start()
    assert p.is_alive() is True
    p.stop()
    p.join()
    assert p.is_alive() is False
    assert p.exitcode == 0


@pytest.mark.timeout(2)  # set a timeout because the test can hang as a failure mode
def test_GenericProcess_can_be_run_and_soft_stopped():
    error_queue = SimpleMultiprocessingQueue()
    p = GenericProcess(error_queue)
    p.start()
    assert p.is_alive() is True
    p.soft_stop()
    p.join()
    assert p.is_alive() is False
    assert p.exitcode == 0


@pytest.mark.timeout(2)  # set a timeout because the test can hang as a failure mode
def test_GenericProcess__run_can_be_executed_just_once(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = GenericProcess(error_queue)
    spied_is_stopped = mocker.spy(p, "is_stopped")
    p.run(num_iterations=1)
    spied_is_stopped.assert_called_once()


@pytest.mark.timeout(2)  # set a timeout because the test can hang as a failure mode
def test_GenericProcess__run_can_be_executed_just_four_cycles(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = GenericProcess(error_queue)
    spied_is_stopped = mocker.spy(p, "is_stopped")
    p.run(num_iterations=4)
    assert spied_is_stopped.call_count == 4


def test_GenericProcess_run_calls___commands_for_each_run_iteration(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = GenericProcess(error_queue)
    spied_commands_for_each_run_iteration = mocker.spy(
        p, "_commands_for_each_run_iteration"
    )
    mocker.patch.object(p, "is_stopped", autospec=True, return_value=True)
    p.run()
    assert spied_commands_for_each_run_iteration.call_count == 1


def test_GenericProcess__queue_is_populated_with_error_occuring_during_run__and_stop_is_called(
    mocker,
):
    expected_error = ValueError("test message")
    error_queue = SimpleMultiprocessingQueue()
    p = GenericProcess(error_queue)

    mocker.patch.object(
        p, "_commands_for_each_run_iteration", autospec=True, side_effect=expected_error
    )
    spied_stop = mocker.spy(p, "stop")

    p.run()
    assert error_queue.empty() is False
    assert spied_stop.call_count == 1
    actual_error, _ = error_queue.get()
    assert isinstance(actual_error, type(expected_error))
    assert str(actual_error) == str(expected_error)
    # assert actual_error == expected_error # Eli (12/24/19): for some reason this asserting doesn't pass...not sure why....so testing class type and str instead


class GenericProcessThatRasiesError(GenericProcess):
    def _commands_for_each_run_iteration(self):
        raise ValueError("test message")


def test_GenericProcess__queue_is_populated_with_error_occuring_during_live_spawned_run():
    expected_error = ValueError("test message")
    error_queue = SimpleMultiprocessingQueue()
    p = GenericProcessThatRasiesError(error_queue)
    p.start()
    p.join()
    assert error_queue.empty() is False
    actual_error, actual_stack_trace = error_queue.get()
    assert isinstance(actual_error, type(expected_error))
    assert str(actual_error) == str(expected_error)
    assert p.exitcode == 0  # When errors are handled, the error code is 0
    # assert actual_error == expected_error # Eli (12/24/19): for some reason this asserting doesn't pass...not sure why....so testing class type and str instead
    assert 'raise ValueError("test message")' in actual_stack_trace


def test_invoke_process_run_and_check_errors__passes_values(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = GenericProcess(error_queue)
    spied_run = mocker.spy(p, "_commands_for_each_run_iteration")
    invoke_process_run_and_check_errors(p)  # runs once by default
    assert spied_run.call_count == 1

    invoke_process_run_and_check_errors(p, num_iterations=2)
    assert spied_run.call_count == 3


def test_invoke_process_run_and_check_errors__raises_and_logs_error(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = GenericProcessThatRasiesError(error_queue)
    mocked_log = mocker.patch.object(logging, "exception", autospec=True)
    with pytest.raises(ValueError, match="test message"):
        invoke_process_run_and_check_errors(p)
    assert error_queue.empty() is True  # the error should have been popped off the queu
    assert mocked_log.call_count == 1
