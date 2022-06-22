# -*- coding: utf-8 -*-
"""Global constants."""
from __future__ import annotations

import multiprocessing.queues
from queue import Queue
from typing import Any
from typing import TYPE_CHECKING
from typing import Union

NANOSECONDS_PER_CENTIMILLISECOND = 10**4

SECONDS_TO_SLEEP_BETWEEN_CHECKING_QUEUE_SIZE = 0.05
QUEUE_CHECK_TIMEOUT_SECONDS = 0.2

# Eli (11/12/20): not sure why this is needed even though __annotations__ is being imported everywhere, but unresolvable errors were occurring during importing of the package
if TYPE_CHECKING:
    UnionOfThreadingAndMultiprocessingQueue = Union[
        Queue[  # pylint: disable=unsubscriptable-object # Eli (3/12/20) not sure why pylint doesn't recognize this type annotation
            Any
        ],
        multiprocessing.queues.Queue[  # pylint: disable=unsubscriptable-object # Eli (3/12/20) not sure why pylint doesn't recognize this type annotation
            Any
        ],
    ]
else:
    UnionOfThreadingAndMultiprocessingQueue = Union[
        Queue,
        multiprocessing.queues.Queue,
    ]
