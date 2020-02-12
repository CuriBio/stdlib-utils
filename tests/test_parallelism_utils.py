# -*- coding: utf-8 -*-
import logging
import queue

import pytest
from stdlib_utils import InfiniteProcess
from stdlib_utils import invoke_process_run_and_check_errors
from stdlib_utils import SimpleMultiprocessingQueue

from .fixtures_parallelism import InfiniteProcessThatRasiesError
from .fixtures_parallelism import InfiniteThreadThatRasiesError


def test_invoke_process_run_and_check_errors__passes_values_for_InfiniteProcess(mocker):
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcess(error_queue)
    spied_run = mocker.spy(p, "_commands_for_each_run_iteration")
    invoke_process_run_and_check_errors(p)  # runs once by default
    assert spied_run.call_count == 1

    invoke_process_run_and_check_errors(p, num_iterations=2)
    assert spied_run.call_count == 3


def test_invoke_process_run_and_check_errors__raises_and_logs_error_for_InfiniteProcess(
    mocker,
):
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcessThatRasiesError(error_queue)
    mocked_log = mocker.patch.object(logging, "exception", autospec=True)
    with pytest.raises(ValueError, match="test message"):
        invoke_process_run_and_check_errors(p)
    assert error_queue.empty() is True  # the error should have been popped off the queu
    assert mocked_log.call_count == 1


def test_invoke_process_run_and_check_errors__does_not_run_setup_or_teardown_by_default(
    mocker,
):
    error_queue = SimpleMultiprocessingQueue()
    p = InfiniteProcess(error_queue)
    spied_run = mocker.spy(p, "_commands_for_each_run_iteration")
    spied_setup = mocker.spy(p, "_setup_before_loop")
    spied_teardown = mocker.spy(p, "_teardown_after_loop")
    invoke_process_run_and_check_errors(p)  # runs once by default
    assert spied_run.call_count == 1
    assert spied_setup.call_count == 0
    assert spied_teardown.call_count == 0

    invoke_process_run_and_check_errors(p, num_iterations=2)
    assert spied_run.call_count == 3


def test_invoke_process_run_and_check_errors__raises_and_logs_error_for_InfiniteThread(
    mocker,
):
    error_queue = queue.Queue()
    p = InfiniteThreadThatRasiesError(error_queue)
    mocked_log = mocker.patch.object(logging, "exception", autospec=True)
    with pytest.raises(ValueError, match="test message"):
        invoke_process_run_and_check_errors(p)
    assert (
        error_queue.empty() is True
    )  # the error should have been popped off the queue
    assert mocked_log.call_count == 1
