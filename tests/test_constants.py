# -*- coding: utf-8 -*-
import typing

from stdlib_utils import NANOSECONDS_PER_CENTIMILLISECOND
from stdlib_utils import QUEUE_CHECK_TIMEOUT_SECONDS
from stdlib_utils import SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE
from stdlib_utils import UnionOfThreadingAndMultiprocessingQueue


def test_polling_times():

    assert SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE == 0.05
    assert QUEUE_CHECK_TIMEOUT_SECONDS == 0.2


def test_type_aliases():
    # A main purpose of this test is just to confirm they are importable from the package itself
    assert (
        isinstance(
            UnionOfThreadingAndMultiprocessingQueue,
            typing._GenericAlias,  # pylint: disable=protected-access # Eli (11/12/20): not sure of another way to get the type
        )
        is True
    )


def test_conversion_factors():
    assert NANOSECONDS_PER_CENTIMILLISECOND == 10**4
