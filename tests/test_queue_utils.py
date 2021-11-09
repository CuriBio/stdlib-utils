# -*- coding: utf-8 -*-
from collections import deque
import multiprocessing
import queue
from queue import Empty
from queue import Queue
import sys
import time

import pytest
from stdlib_utils import confirm_queue_is_eventually_empty
from stdlib_utils import confirm_queue_is_eventually_of_size
from stdlib_utils import drain_queue
from stdlib_utils import is_queue_eventually_empty
from stdlib_utils import is_queue_eventually_not_empty
from stdlib_utils import is_queue_eventually_of_size
from stdlib_utils import put_object_into_queue_and_raise_error_if_eventually_still_empty
from stdlib_utils import QUEUE_CHECK_TIMEOUT_SECONDS
from stdlib_utils import queue_utils
from stdlib_utils import QueueNotEmptyError
from stdlib_utils import QueueNotExpectedSizeError
from stdlib_utils import QueueStillEmptyError
from stdlib_utils import safe_get
from stdlib_utils import SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE
from stdlib_utils import SimpleMultiprocessingQueue
from stdlib_utils import TestingQueue

# Eli (10/23/20): had to drop support for MacOS because they don't adequately support Multiprocessing queues yet
#     def qsize(self):
#         # Raises NotImplementedError on Mac OSX because of broken sem_getvalue()
# >       return self._maxsize - self._sem._semlock._get_value()
# ./../../hostedtoolcache/Python/3.8.6/x64/lib/python3.8/multiprocessing/queues.py:120: NotImplementedError
skip_on_mac = pytest.mark.skipif(
    sys.platform.startswith("darwin"),
    reason="the queue.qsize method is Not Implemented on MacOS",
)


def test_SimpleMultiprocessingQueue__get_nowait__returns_value_if_present():
    test_queue = SimpleMultiprocessingQueue()
    expected = "blah"
    test_queue.put(expected)
    actual = test_queue.get_nowait()
    assert actual == expected


def test_SimpleMultiprocessingQueue__put_nowait__adds_value_to_queue():
    test_queue = SimpleMultiprocessingQueue()
    expected = "blah7"
    test_queue.put_nowait(expected)
    actual = test_queue.get_nowait()
    assert actual == expected


@pytest.mark.timeout(0.1)  # set a timeout because the test can hang as a failure mode
def test_SimpleMultiprocessingQueue__get_nowait__raises_error_if_empty():
    test_queue = SimpleMultiprocessingQueue()
    with pytest.raises(queue.Empty):
        test_queue.get_nowait()


@pytest.mark.parametrize(
    ",".join(("test_queue", "test_size", "expected", "test_description")),
    [
        (
            queue.Queue(),
            0,
            True,
            "given_empty_threading_queue__when_called_with_zero__returns_true",
        ),
        (
            multiprocessing.Queue(),
            0,
            True,
            "Given empty multiprocessing queue, When called with zero, Then it returns true",
        ),
        (
            queue.Queue(),
            0,
            True,
            "Given empty threading queue, When called with 1, Then it returns false",
        ),
        (
            multiprocessing.Queue(),
            0,
            True,
            "Given empty multiprocessing queue, When called with 1, Then it returns false",
        ),
    ],
)
@skip_on_mac
def test_is_queue_eventually_of_size(test_queue, test_size, expected, test_description):
    assert is_queue_eventually_of_size(test_queue, test_size) is expected


@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
@skip_on_mac
def test_is_queue_eventually_of_size__given_populated_queue__when_caled_with_zero__then_it_returns_false(
    test_queue, test_description
):
    test_queue.put("bob")
    assert is_queue_eventually_of_size(test_queue, 0) is False


@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
@skip_on_mac
def test_is_queue_eventually_of_size__given_populated_queue__when_caled_with_one__then_it_returns_true(
    test_queue, test_description
):
    test_queue.put("bob")
    assert is_queue_eventually_of_size(test_queue, 1) is True


@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
def test_is_queue_eventually_of_size__given_empty_queue_that_has_qsize_mocked__when_called_with_1__returns_true_after_several_calls(
    test_queue, test_description, mocker
):
    mocked_qsize = mocker.patch.object(test_queue, "qsize", autospec=True, side_effect=[0, 0, 0, 1])
    assert is_queue_eventually_of_size(test_queue, 1) is True
    assert mocked_qsize.call_count == 4


@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
def test_is_queue_eventually_of_size__given_empty_queue__when_called_with_1__returns_false_after_kwarg_timeout_is_met(
    test_queue,
    test_description,
    mocker,
):
    mocked_qsize = mocker.patch.object(
        test_queue, "qsize", autospec=True, return_value=0
    )  # Eli (10/23/20: Mocking instead of spying on qsize so that this can be run on a Mac to check code coverage. As of today, MacOS has not implemented qsize().
    mocker.patch.object(
        queue_utils,
        "process_time",
        autospec=True,
        side_effect=[
            0,
            0.1,
            0.15 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 1,
            0.2 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 2,
            0.3 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 3,
            0.35 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 4,
            0.4 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 5,
            0.45 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 6,
        ],
    )
    assert is_queue_eventually_of_size(test_queue, 1, timeout_seconds=0.41) is False
    assert mocked_qsize.call_count == 6


def test_is_queue_eventually_empty__returns_true_with_empty_threading_queue():
    q = queue.Queue()
    assert is_queue_eventually_empty(q) is True


def test_is_queue_eventually_empty__returns_true_with_empty_multiprocessing_queue__after_just_one_call(
    mocker,
):
    q = multiprocessing.Queue()
    spied_empty = mocker.spy(q, "empty")
    assert is_queue_eventually_empty(q) is True
    assert spied_empty.call_count == 1


def test_is_queue_eventually_empty__returns_false_with_not_empty_threading_queue(
    mocker,
):
    q = queue.Queue()
    mocked_empty = mocker.patch.object(q, "empty", autospec=True, return_value=False)
    assert (
        is_queue_eventually_empty(q, timeout_seconds=SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 6)
        is False
    )
    assert mocked_empty.call_count > 5


def test_is_queue_eventually_empty__returns_false_with_not_empty_threading_queue__after_kwarg_timeout_is_met(
    mocker,
):
    q = queue.Queue()
    mocked_empty = mocker.patch.object(q, "empty", autospec=True, return_value=False)
    mocker.patch.object(
        queue_utils,
        "process_time",
        autospec=True,
        side_effect=[
            0,
            0.1,
            0.15 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 1,
            0.2 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 2,
            0.3 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 3,
            0.35 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 4,
            0.4 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 5,
        ],
    )
    assert is_queue_eventually_empty(q, timeout_seconds=0.36) is False
    assert mocked_empty.call_count == 5


def test_is_queue_eventually_empty__returns_true_after_multiple_attempts_with_eventually_empty_threading_queue(
    mocker,
):
    q = queue.Queue()
    mocked_empty = mocker.patch.object(q, "empty", autospec=True, side_effect=[False, False, False, True])
    assert is_queue_eventually_empty(q) is True
    assert mocked_empty.call_count == 4


def test_is_queue_eventually_not_empty__returns_true_with_not_empty_threading_queue__after_just_one_call(
    mocker,
):
    q = queue.Queue()
    q.put("bob")
    spied_empty = mocker.spy(q, "empty")
    time.sleep(0.1)  # just to be safe make sure thread is definitely populated
    assert is_queue_eventually_not_empty(q) is True
    assert spied_empty.call_count == 1


def test_is_queue_eventually_not_empty__returns_true_with_not_empty_multiprocessing_queue():
    q = multiprocessing.Queue()
    q.put("bill")
    time.sleep(0.1)  # just to be safe make sure thread is definitely populated
    assert is_queue_eventually_not_empty(q) is True


def test_is_queue_eventually_not_empty__returns_false_with_empty_threading_queue(
    mocker,
):
    q = queue.Queue()
    spied_empty = mocker.spy(q, "empty")
    assert (
        is_queue_eventually_not_empty(q, timeout_seconds=SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 3)
        is False
    )
    assert spied_empty.call_count > 2


def test_is_queue_eventually_not_empty__returns_false_with_empty_threading_queue__after_kwarg_timeout_is_met(
    mocker,
):
    q = queue.Queue()
    spied_empty = mocker.spy(q, "empty")
    mocker.patch.object(
        queue_utils,
        "process_time",
        autospec=True,
        side_effect=[
            0,
            0.1,
            0.15 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 1,
            0.2 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 2,
            0.3 - SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE * 3,
        ],
    )
    assert is_queue_eventually_not_empty(q, timeout_seconds=0.25) is False
    assert spied_empty.call_count == 3


def test_is_queue_eventually_not_empty__returns_true_after_multiple_attempts_with_eventually_not_empty_threading_queue(
    mocker,
):
    q = queue.Queue()
    mocked_empty = mocker.patch.object(q, "empty", autospec=True, side_effect=[True, True, True, False])
    assert is_queue_eventually_not_empty(q) is True
    assert mocked_empty.call_count == 4


def test_safe_get__returns_expected_items():
    expected_items = ["item1", "item2", "item3"]
    actual_items = []

    q = Queue()
    for item in expected_items:
        q.put(item)

    num_items = len(expected_items)
    for _ in range(num_items + 1):
        next_item = safe_get(q)
        actual_items.append(next_item)

    expected_items.append(None)
    assert actual_items == expected_items


def test_safe_get__calls_queue_get_correctly(mocker):
    q = Queue()
    spied_get = mocker.spy(q, "get")

    expected_timeout = 2.3
    safe_get(q, timeout_seconds=expected_timeout)
    assert spied_get.call_args[1]["timeout"] == expected_timeout
    assert spied_get.call_args[1]["block"] is True


def test_safe_get__used_default_queue_get_timeout_if_timeout_seconds_not_given(mocker):
    q = Queue()
    spied_get = mocker.spy(q, "get")
    safe_get(q)
    assert spied_get.call_args[1]["timeout"] == QUEUE_CHECK_TIMEOUT_SECONDS


def test_drain_queue__calls_queue_get_correctly(mocker):
    q = Queue()
    q.put(1)
    spied_get = mocker.spy(q, "get")

    expected_timeout = 5.9
    drain_queue(q, timeout_seconds=expected_timeout)
    assert spied_get.call_args[1]["timeout"] == expected_timeout
    assert spied_get.call_args[1]["block"] is True


def test_drain_queue__used_default_queue_get_timeout_if_timeout_seconds_not_given(
    mocker,
):
    q = Queue()
    q.put("item")
    spied_get = mocker.spy(q, "get")
    drain_queue(q)
    assert spied_get.call_args[1]["timeout"] == QUEUE_CHECK_TIMEOUT_SECONDS


def test_put_object_into_queue_and_raise_error_if_eventually_still_empty__puts_object_into_queue():
    expected = "bob"
    q = Queue()
    put_object_into_queue_and_raise_error_if_eventually_still_empty(expected, q)
    actual = q.get_nowait()
    assert actual == expected


def test_put_object_into_queue_and_raise_error_if_eventually_still_empty__raises_error_if_queue_not_populated(
    mocker,
):
    q = Queue()
    mocker.patch.object(q, "put", autospec=True)
    with pytest.raises(QueueStillEmptyError):
        put_object_into_queue_and_raise_error_if_eventually_still_empty("bill", q)


def test_put_object_into_queue_and_raise_error_if_eventually_still_empty__passes_timeout_kwarg_to_subfunction(
    mocker,
):
    expected = 2.2
    q = Queue()
    spied_not_empty = mocker.spy(queue_utils, "is_queue_eventually_not_empty")
    put_object_into_queue_and_raise_error_if_eventually_still_empty("bill", q, timeout_seconds=expected)
    spied_not_empty.assert_called_once_with(q, timeout_seconds=expected)


@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
def test_confirm_queue_is_eventually_of_size__passes_args_to_is_queue_eventually_of_size(
    test_queue,
    test_description,
    mocker,
):
    mocked_is_queue_eventually_of_size = mocker.patch.object(
        queue_utils, "is_queue_eventually_of_size", autospec=True, return_value=True
    )  # mocking instead of spying so that code coverage can still happen on MacOS which doesn't support queue.qsize
    expected_size = 3
    expected_timeout = 0.07
    confirm_queue_is_eventually_of_size(test_queue, expected_size, timeout_seconds=expected_timeout)
    mocked_is_queue_eventually_of_size.assert_called_once_with(
        test_queue, expected_size, timeout_seconds=expected_timeout
    )


@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
def test_confirm_queue_is_eventually_of_size__returns_without_error_if_queue_is_of_size(
    test_queue,
    test_description,
    mocker,
):
    mocker.patch.object(
        queue_utils, "is_queue_eventually_of_size", autospec=True, return_value=True
    )  # mocking instead of spying so that code coverage can still happen on MacOS which doesn't support queue.qsize

    expected_size = 0
    expected_timeout = 0.07
    assert (
        confirm_queue_is_eventually_of_size(test_queue, expected_size, timeout_seconds=expected_timeout)
        is None
    )


@skip_on_mac
@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
def test_confirm_queue_is_eventually_of_size__raises_error_if_queue_is_not_expected_size__when_zero_elements(
    test_queue, test_description
):
    expected_size = 1
    with pytest.raises(
        QueueNotExpectedSizeError,
        match=f"expected to contain {expected_size} objects but actually contained 0 objects",
    ):
        confirm_queue_is_eventually_of_size(test_queue, expected_size, timeout_seconds=0.01)


@skip_on_mac
@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
def test_confirm_queue_is_eventually_of_size__raises_error_if_queue_is_not_expected_size__when_one_object_in_queue(
    test_queue, test_description
):
    expected_size = 2
    test_queue.put("blah")
    time.sleep(0.1)  # make sure the object is in the queue
    with pytest.raises(
        QueueNotExpectedSizeError,
        match=f"expected to contain {expected_size} objects but actually contained 1 objects",
    ):
        confirm_queue_is_eventually_of_size(test_queue, expected_size, timeout_seconds=0.01)


@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
def test_confirm_queue_is_eventually_of_size__given_qsize_is_mocked__then_raises_error_if_queue_is_not_expected_size__when_zero_elements(
    test_queue,
    test_description,
    mocker,
):
    # mock qsize so test can run on a Mac
    expected_size = 1
    mocker.patch.object(test_queue, "qsize", autospec=True, return_value=0)
    with pytest.raises(
        QueueNotExpectedSizeError,
        match=f"expected to contain {expected_size} objects but actually contained 0 objects",
    ):
        confirm_queue_is_eventually_of_size(test_queue, expected_size, timeout_seconds=0.01)


@skip_on_mac
@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
def test_confirm_queue_is_eventually_empty__raises_error_if_queue_is_not_empty__when_one_object_in_queue(
    test_queue, test_description
):
    expected_obj = "blah"
    test_queue.put(expected_obj)
    time.sleep(0.1)  # make sure the object is in the queue
    with pytest.raises(
        QueueNotEmptyError,
        match=f"expected to be empty but actually contained 1 objects. The first object was {expected_obj}",
    ):
        confirm_queue_is_eventually_empty(test_queue, timeout_seconds=0.01)


@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
def test_confirm_queue_is_eventually_empty__given_qsize_is_mocked__then_raises_error_if_queue_is_not_expected_size__when_one_element(
    test_queue,
    test_description,
    mocker,
):
    # mock qsize so test can run on a Mac
    mocker.patch.object(test_queue, "qsize", autospec=True, return_value=1)
    test_queue.put("blarg")
    time.sleep(0.1)  # make sure the object is in the queue

    with pytest.raises(
        QueueNotEmptyError,
        match="expected to be empty but actually contained 1 objects",
    ):
        confirm_queue_is_eventually_empty(test_queue, timeout_seconds=0.01)


@pytest.mark.parametrize(
    ",".join(("test_queue", "test_description")),
    [
        (queue.Queue(), "threading queue"),
        (multiprocessing.Queue(), "multiprocessing queue"),
    ],
)
def test_confirm_queue_is_eventually_empty__passes_args_to_is_queue_eventually_of_size(
    test_queue,
    test_description,
    mocker,
):
    mocked_is_queue_eventually_of_size = mocker.patch.object(
        queue_utils, "is_queue_eventually_of_size", autospec=True, return_value=True
    )  # mocking instead of spying so that code coverage can still happen on MacOS which doesn't support queue.qsize
    expected_timeout = 0.07
    confirm_queue_is_eventually_empty(test_queue, timeout_seconds=expected_timeout)
    mocked_is_queue_eventually_of_size.assert_called_once_with(
        test_queue, 0, timeout_seconds=expected_timeout
    )


def test_TestingQueue__is_a_deque(mocker):
    assert isinstance(TestingQueue(), deque) is True


def test_TestingQueue__raises_TypeError_if_indexed():
    tq = TestingQueue()
    tq.put(1)
    with pytest.raises(TypeError, match="'TestingQueue' object is not subscriptable"):
        tq[0]  # pylint: disable=pointless-statement  # Tanner (11/9/21): indexing will raise error


def test_TestingQueue__raises_TypeError_if_passed_to_len():
    with pytest.raises(TypeError, match="object of type 'TestingQueue' has no len()"):
        len(TestingQueue())


def test_TestingQueue_put__calls_append_on_self_and_excepts_kwargs_of_normal_queue_put_method(
    mocker,
):
    tq = TestingQueue()
    mocked_append = mocker.spy(tq, "append")

    expected_item = "item"
    tq.put(expected_item, block=None, timeout=None)
    mocked_append.assert_called_once_with(expected_item)


def test_TestingQueue_put_nowait__calls_append_on_self(mocker):
    tq = TestingQueue()
    mocked_append = mocker.spy(tq, "append")

    expected_item = 100
    tq.put_nowait(expected_item)
    mocked_append.assert_called_once_with(expected_item)


def test_TestingQueue_get__calls_popleft_on_self_and_excepts_kwargs_of_normal_queue_put_method(
    mocker,
):
    tq = TestingQueue()
    mocked_popleft = mocker.spy(tq, "popleft")

    expected_item = {"test": "item"}
    tq.append(expected_item)
    tq.popleft()
    mocked_popleft.assert_called_once_with()


def test_TestingQueue_get__raises_error_if_queue_is_empty():
    with pytest.raises(Empty):
        TestingQueue().get()


def test_TestingQueue_get_nowait__calls_append_on_self(mocker):
    tq = TestingQueue()
    mocked_popleft = mocker.spy(tq, "popleft")

    expected_item = ""
    tq.put(expected_item)
    tq.append(expected_item)
    tq.popleft()
    mocked_popleft.assert_called_once_with()


def test_TestingQueue_get_nowait__raises_error_if_queue_is_empty():
    with pytest.raises(Empty):
        TestingQueue().get_nowait()


def test_TestingQueue_qsize__returns_correct_value():
    tq = TestingQueue()
    tq.put(1)
    tq.put(2)
    assert tq.qsize() == 2


def test_TestingQueue_empty__returns_correct_values():
    tq = TestingQueue()
    assert tq.empty() is True
    tq.put(1)
    assert tq.empty() is False
    tq.get()
    assert tq.empty() is True
