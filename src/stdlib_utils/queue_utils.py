# -*- coding: utf-8 -*-
"""Functionality to enhance checking of queue mainly during unit testing.

This module should not need to import from any other modules in
stdlib_utils.
"""
from __future__ import annotations

from collections import deque
import multiprocessing
import multiprocessing.queues
import queue
from queue import Empty
from queue import Queue
import time
from time import process_time
from typing import Any
from typing import List
from typing import Union

from .constants import QUEUE_CHECK_TIMEOUT_SECONDS
from .constants import SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE
from .constants import UnionOfThreadingAndMultiprocessingQueue
from .exceptions import QueueNotEmptyError
from .exceptions import QueueNotExpectedSizeError
from .exceptions import QueueStillEmptyError


def _eventually_empty(
    should_be_empty: bool,
    the_queue: UnionOfThreadingAndMultiprocessingQueue,
    timeout_seconds: Union[float, int] = QUEUE_CHECK_TIMEOUT_SECONDS,
) -> bool:
    """Help to determine if queue is eventually empty or not."""
    start_time = process_time()
    while process_time() - start_time < timeout_seconds:
        is_empty = the_queue.empty()
        value_to_check = is_empty
        if not should_be_empty:
            value_to_check = not value_to_check
        if value_to_check:
            return True
        time.sleep(
            SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE
        )  # wait 50 msec between polling the queue to allow things to process in the background
        # process_time() does not include time during sleep, so decrement the timeout_seconds to account for this
        timeout_seconds -= SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE
    return False


def is_queue_eventually_empty(
    the_queue: UnionOfThreadingAndMultiprocessingQueue,
    timeout_seconds: Union[float, int] = QUEUE_CHECK_TIMEOUT_SECONDS,
) -> bool:
    """Check if queue is empty prior to timeout occurring."""
    return _eventually_empty(True, the_queue, timeout_seconds=timeout_seconds)


def is_queue_eventually_not_empty(
    the_queue: UnionOfThreadingAndMultiprocessingQueue,
    timeout_seconds: Union[float, int] = QUEUE_CHECK_TIMEOUT_SECONDS,
) -> bool:
    """Check if queue is not empty prior to timeout occurring."""
    return _eventually_empty(False, the_queue, timeout_seconds=timeout_seconds)


def is_queue_eventually_of_size(
    the_queue: UnionOfThreadingAndMultiprocessingQueue,
    size: int,
    timeout_seconds: Union[float, int] = QUEUE_CHECK_TIMEOUT_SECONDS,
) -> bool:
    """Check if queue is a certain size prior to timeout occurring.

    Typically used in unit testing to ensure that a put or get operation
    has fully completed during test setup before triggering the function
    being tested.
    """
    start_time = process_time()
    while process_time() - start_time < timeout_seconds:
        if the_queue.qsize() == size:
            return True
        time.sleep(
            SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE
        )  # wait 50 msec between polling the queue to allow things to process in the background
        # process_time() does not include time during sleep, so decrement the timeout_seconds to account for this
        timeout_seconds -= SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE
    return False


def confirm_queue_is_eventually_of_size(
    the_queue: UnionOfThreadingAndMultiprocessingQueue,
    size: int,
    timeout_seconds: Union[float, int] = QUEUE_CHECK_TIMEOUT_SECONDS,
) -> None:
    """Raise exception if queue is not a certain size prior to timeout.

    Typically used in unit testing to ensure that a put or get operation
    has fully completed during test setup before triggering the function
    being tested.
    """
    if is_queue_eventually_of_size(the_queue, size, timeout_seconds=timeout_seconds):
        return
    raise QueueNotExpectedSizeError(the_queue, size)


def confirm_queue_is_eventually_empty(
    the_queue: UnionOfThreadingAndMultiprocessingQueue,
    timeout_seconds: Union[float, int] = QUEUE_CHECK_TIMEOUT_SECONDS,
) -> None:
    """Raise exception if queue is not empty prior to timeout.

    Typically used in unit testing to ensure that a get operation has
    fully completed during test setup before triggering the function
    being tested or that all items in a queue were processed by the main
    code.
    """
    if is_queue_eventually_of_size(the_queue, 0, timeout_seconds=timeout_seconds):
        return

    raise QueueNotEmptyError(the_queue)


def put_object_into_queue_and_raise_error_if_eventually_still_empty(  # pylint: disable=invalid-name # Eli (10/22/20): I know this is long, but it's a combined helper function for unit testing
    obj: object,
    the_queue: UnionOfThreadingAndMultiprocessingQueue,
    timeout_seconds: Union[float, int] = QUEUE_CHECK_TIMEOUT_SECONDS,
) -> None:
    """Put an object into a queue and wait until queue is populated.

    Raises an error if queue is still empty and the end of
    timeout_seconds. This is primarily/exclusively used in unit testing.
    """
    the_queue.put(obj)
    if not is_queue_eventually_not_empty(the_queue, timeout_seconds=timeout_seconds):
        raise QueueStillEmptyError()


def safe_get(
    the_queue: Queue[Any],  # pylint: disable=unsubscriptable-object
    timeout_seconds: Union[float, int] = QUEUE_CHECK_TIMEOUT_SECONDS,
) -> Any:
    try:
        return the_queue.get(block=True, timeout=timeout_seconds)
    except Empty:
        return None


def drain_queue(
    the_queue: Queue[Any],  # pylint: disable=unsubscriptable-object
    timeout_seconds: Union[float, int] = QUEUE_CHECK_TIMEOUT_SECONDS,
) -> List[Any]:
    queue_items = list()
    item = safe_get(the_queue, timeout_seconds=timeout_seconds)
    while item is not None:
        queue_items.append(item)
        item = safe_get(the_queue, timeout_seconds=timeout_seconds)
    return queue_items


class SimpleMultiprocessingQueue(multiprocessing.queues.SimpleQueue):  # type: ignore[type-arg] # noqa: F821 # Eli (3/10/20) can't figure out why SimpleQueue doesn't have type arguments defined in the stdlib(?)
    """Some additional basic functionality.

    Since SimpleQueue is not technically a class, there are some tricks to subclassing it: https://stackoverflow.com/questions/39496554/cannot-subclass-multiprocessing-queue-in-python-3-5
    """

    def __init__(self) -> None:
        ctx = multiprocessing.get_context()
        super().__init__(ctx=ctx)

    def get_nowait(self) -> Any:
        """Get value or raise error if empty."""
        if self.empty():
            raise queue.Empty()
        return self.get()

    def put_nowait(self, obj: Any) -> None:
        """Put without waiting/blocking.

        This is the only option with a SimpleQueue, but this is aliased
        to put to make the interface compatible with the regular
        multiprocessing.Queue interface.
        """
        self.put(obj)


class TestingQueue(deque):  # type: ignore[type-arg]
    """Queue-like Deque subclass.

    Provides faster operations in place of a real queue, but with the same methods as a queue

    This should only be used in tests where thread/process safety isn't
    an issue.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    # Override deque dunder methods so they are not accidentally used

    def __getitem__(self, i):  # type: ignore
        raise TypeError("'TestingQueue' object is not subscriptable")

    def __len__(self):  # type: ignore
        raise TypeError("object of type 'TestingQueue' has no len()")

    # Queue methods

    def put(self, item: Any, block: bool = False, timeout: int = 0) -> None:
        # pylint: disable=unused-argument  # Tanner (8/23/21): This is intentional to make this compatible with code expecting real queues
        self.append(item)

    def put_nowait(self, item: Any) -> None:
        self.append(item)

    def get(self, block: bool = False, timeout: int = 0) -> Any:
        # pylint: disable=unused-argument  # Tanner (8/23/21): This is intentional to make this compatible with code expecting real queues
        return self.get_nowait()

    def get_nowait(self) -> Any:
        if self.empty():
            raise Empty()
        return self.popleft()

    def qsize(self) -> int:
        return super().__len__()

    def empty(self) -> bool:
        return self.qsize() == 0
