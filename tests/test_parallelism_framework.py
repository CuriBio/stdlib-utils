# -*- coding: utf-8 -*-
import logging
import queue
import threading
import time

import pytest
from stdlib_utils import InfiniteLoopingParallelismMixIn
from stdlib_utils import invoke_process_run_and_check_errors
from stdlib_utils import is_queue_eventually_empty
from stdlib_utils import is_queue_eventually_not_empty
from stdlib_utils import NANOSECONDS_PER_CENTIMILLISECOND
from stdlib_utils import parallelism_framework
from stdlib_utils import SimpleMultiprocessingQueue


def generic_infinite_looper():
    p = InfiniteLoopingParallelismMixIn(
        queue.Queue(),
        logging.INFO,
        threading.Event(),
        threading.Event(),
        threading.Event(),
        threading.Event(),
        threading.Event(),
        minimum_iteration_duration_seconds=0.01,
    )
    return p


def simple_infinite_looper():
    p = InfiniteLoopingParallelismMixIn(
        SimpleMultiprocessingQueue(),
        logging.INFO,
        threading.Event(),
        threading.Event(),
        threading.Event(),
        threading.Event(),
        threading.Event(),
        minimum_iteration_duration_seconds=0.01,
    )
    return p


def test_InfiniteLoopingParallelismMixIn__sleeps_during_loop_for_time_remaining_if_minimum_iteration_duration_not_met(
    mocker,
):
    mocked_length_of_time_to_execute_ns = 10**6
    mocker.patch.object(
        time,
        "perf_counter_ns",
        autospec=True,
        side_effect=[0, 0, 0, mocked_length_of_time_to_execute_ns, 0],
    )
    mocked_sleep = mocker.patch.object(time, "sleep", autospec=True)
    generic_infinite_looper().run(num_iterations=2, perform_setup_before_loop=True)
    expected_time_to_sleep_seconds = round(0.01 - mocked_length_of_time_to_execute_ns / 10**9, 10)
    mocked_sleep.assert_called_once_with(expected_time_to_sleep_seconds)


def test_InfiniteLoopingParallelismMixIn__does_not_sleep_during_loop_if_minimum_iteration_duration_already_met(
    mocker,
):

    mocker.patch.object(
        time,
        "perf_counter_ns",
        autospec=True,
        side_effect=[0, 0, 0, 0.1 * 10**9, 0],
    )
    mocked_sleep = mocker.patch.object(time, "sleep", autospec=True)
    generic_infinite_looper().run(num_iterations=2, perform_setup_before_loop=True)
    assert mocked_sleep.call_count == 0


def test_InfiniteLoopingParallelismMixIn__reset_performance_tracker__initially_returns_start_timepoint_of_measurements_from_setup_before_loop__then_last_reset_value(
    mocker,
):
    expected_first_return = 12345
    expected_second_return = 54321
    mocker.patch.object(
        time,
        "perf_counter_ns",
        autospec=True,
        side_effect=[expected_first_return, 0, 0, 0, expected_second_return, 0, 0],
    )

    p = generic_infinite_looper()
    invoke_process_run_and_check_errors(p, perform_setup_before_loop=True)

    actual_first_return = p.reset_performance_tracker()
    assert "start_timepoint_of_measurements" in actual_first_return
    assert actual_first_return["start_timepoint_of_measurements"] == expected_first_return
    assert "idle_iteration_time_ns" in actual_first_return
    assert actual_first_return["idle_iteration_time_ns"] == 0

    actual_second_return = p.reset_performance_tracker()
    assert "start_timepoint_of_measurements" in actual_second_return
    assert actual_second_return["start_timepoint_of_measurements"] == expected_second_return


def test_InfiniteLoopingParallelismMixIn__reset_performance_tracker__returns_idle_time(
    mocker,
):
    p = generic_infinite_looper()
    dur_of_first_iter_ns = 2 * 10**6
    dur_of_second_iter_ns = 1 * 10**6
    mocker.patch.object(
        parallelism_framework,
        "calculate_iteration_time_ns",
        autospec=True,
        side_effect=[dur_of_first_iter_ns, dur_of_second_iter_ns],
    )
    mocker.patch.object(time, "sleep", autospec=True)  # mock sleep to speed up test

    p.run(num_iterations=3, perform_setup_before_loop=True)

    performance_metrics = p.reset_performance_tracker()
    total_idle_time = performance_metrics["idle_iteration_time_ns"]
    allowed_time_per_iter_ns = 10 * 10**6
    expected_idle_time = allowed_time_per_iter_ns * 2 - dur_of_first_iter_ns - dur_of_second_iter_ns
    assert total_idle_time == expected_idle_time


def test_InfiniteLoopingParallelismMixIn__reset_performance_tracker__returns_and_stores_percent_use(
    mocker,
):
    p = generic_infinite_looper()
    percent_use_values = p.get_percent_use_values()

    spied_elapsed_time = mocker.spy(p, "get_elapsed_time_since_last_performance_measurement")

    p.run(num_iterations=3)
    idle_time_secs = p.get_idle_time_ns()
    actual_first_return = p.reset_performance_tracker()
    expected_percent_use_1 = 100 * (1 - idle_time_secs / spied_elapsed_time.spy_return)
    assert actual_first_return["percent_use"] == expected_percent_use_1
    assert percent_use_values[0] == expected_percent_use_1

    p.run(num_iterations=5)
    idle_time_secs = p.get_idle_time_ns()
    actual_second_return = p.reset_performance_tracker()
    expected_percent_use_2 = 100 * (1 - idle_time_secs / spied_elapsed_time.spy_return)
    assert actual_second_return["percent_use"] == expected_percent_use_2
    assert percent_use_values[1] == expected_percent_use_2


def test_InfiniteLoopingParallelismMixIn__get_start_timepoint_of_performance_measurement(
    mocker,
):
    expected_timepoint = 123554
    mocker.patch.object(
        time,
        "perf_counter_ns",
        autospec=True,
        side_effect=[expected_timepoint, 0, 0],
    )

    p = generic_infinite_looper()
    invoke_process_run_and_check_errors(p, perform_setup_before_loop=True)
    actual_timepoint = p.get_start_timepoint_of_performance_measurement()
    assert actual_timepoint == expected_timepoint


def test_InfiniteLoopingParallelismMixIn__hard_stop__calls_stop(mocker):
    p = generic_infinite_looper()
    spied_stop = mocker.spy(p, "stop")

    p.hard_stop()
    assert p.is_stopped() is True
    spied_stop.assert_called_once()


def test_InfiniteLoopingParallelismMixIn__hard_stop__waits_for_teardown_complete_event_to_drain_error_queue(
    mocker,
):
    expected_error = "dummy_error"

    p = generic_infinite_looper()
    error_queue = p.get_fatal_error_reporter()
    error_queue.put(expected_error)

    def side_effect(*args, **kwargs):
        assert is_queue_eventually_not_empty(error_queue) is True
        return True

    mocker.patch.object(p, "is_teardown_complete", autospec=True, side_effect=side_effect)

    actual = p.hard_stop()
    assert actual["fatal_error_reporter"] == [expected_error]
    assert is_queue_eventually_empty(error_queue) is True


def test_InfiniteLoopingParallelismMixIn__hard_stop__waits_for_teardown_complete_event_to_drain_error_queue_with_SimpleMultiprocessingQueue(
    mocker,
):
    expected_error = "dummy_error"

    p = simple_infinite_looper()
    error_queue = p.get_fatal_error_reporter()
    error_queue.put(expected_error)

    def side_effect(*args, **kwargs):
        assert is_queue_eventually_not_empty(error_queue) is True
        return True

    mocked_complete = mocker.patch.object(p, "is_teardown_complete", autospec=True, side_effect=side_effect)

    actual = p.hard_stop()
    assert actual["fatal_error_reporter"] == [expected_error]
    assert error_queue.empty() is True

    mocked_complete.assert_called_once()


@pytest.mark.timeout(1)
def test_InfiniteLoopingParallelismMixIn__hard_stop__timeout_overrides_waiting_for_teardown_complete_event_to_drain_error_queue(
    mocker,
):
    expected_error = "dummy_error"

    p = generic_infinite_looper()
    error_queue = p.get_fatal_error_reporter()

    def side_effect(*args, **kwargs):
        assert is_queue_eventually_not_empty(error_queue) is True
        return False

    mocked_complete = mocker.patch.object(p, "is_teardown_complete", autospec=True, side_effect=side_effect)
    error_queue.put(expected_error)

    actual = p.hard_stop(timeout=0.2)
    assert actual["fatal_error_reporter"] == [expected_error]
    assert error_queue.empty() is True

    mocked_complete.assert_called()


@pytest.mark.parametrize(
    "perform_setup_before_loop,test_description",
    [
        (False, "sets start_up_complete_event with no setup before loop"),
        (True, "sets start_up_complete_event with setup before loop"),
    ],
)
def test_InfiniteLoopingParallelismMixIn__always_sets_start_up_complete_event_before_entering_loop(
    perform_setup_before_loop, test_description, mocker
):
    p = generic_infinite_looper()
    assert p.is_start_up_complete() is False
    p.run(num_iterations=1, perform_setup_before_loop=perform_setup_before_loop)
    assert p.is_start_up_complete() is True


def test_InfiniteLoopingParallelismMixIn__get_percent_use_metrics__returns_correct_values(
    mocker,
):
    p = generic_infinite_looper()

    # create percent use values
    p.run(num_iterations=10)
    p.reset_performance_tracker()
    p.run(num_iterations=10)
    p.reset_performance_tracker()
    p.run(num_iterations=10)
    p.reset_performance_tracker()

    expected_percent_use_vals = p.get_percent_use_values()

    actual = p.get_percent_use_metrics()
    assert actual["max"] == max(expected_percent_use_vals)
    assert actual["min"] == min(expected_percent_use_vals)
    assert actual["mean"] == round(sum(expected_percent_use_vals) / len(expected_percent_use_vals), 6)


def test_InfiniteLoopingParallelismMixIn__reset_performance_tracker__returns_longest_iterations(
    mocker,
):
    expected_longest_times = list(range(1, 6))

    p = generic_infinite_looper()

    iteration_times = [0 for _ in range(p.num_longest_iterations)]
    iteration_times.extend(expected_longest_times)
    mocker.patch.object(
        parallelism_framework,
        "calculate_iteration_time_ns",
        autospec=True,
        side_effect=iteration_times,
    )

    p.run(num_iterations=len(iteration_times) + 1)

    actual = p.reset_performance_tracker()
    assert actual["longest_iterations"] == expected_longest_times


def test_InfiniteLoopingParallelismMixIn__pause__does_not_call_commands_for_each_run_iteration_when_paused__and_sets_pause_event_to_true__then_resume_sets_event_to_false_and_commands_are_allowed_again(
    mocker,
):
    p = generic_infinite_looper()
    spied_commands = mocker.spy(p, "_commands_for_each_run_iteration")
    p.pause()

    assert p.is_paused() is True
    invoke_process_run_and_check_errors(p)

    assert spied_commands.call_count == 0

    p.resume()

    assert p.is_paused() is False

    invoke_process_run_and_check_errors(p)

    assert spied_commands.call_count == 1


def test_InfiniteLoopingParallelismMixIn__correctly_stores_time_since_initialized__in_setup_before_loop(
    mocker,
):
    p = generic_infinite_looper()

    expected_init_time = 15796649135715
    expected_poll_time = 15880317595302
    mocker.patch.object(
        parallelism_framework.time,
        "perf_counter_ns",
        autospec=True,
        side_effect=[0, expected_init_time, 0, expected_poll_time],
    )

    # before setup
    assert p.get_cms_since_init() == 0

    invoke_process_run_and_check_errors(p, perform_setup_before_loop=True)
    # after setup
    expected_dur_since_init = (expected_poll_time - expected_init_time) // NANOSECONDS_PER_CENTIMILLISECOND
    assert p.get_cms_since_init() == expected_dur_since_init
