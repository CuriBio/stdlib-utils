# -*- coding: utf-8 -*-
"""Utilities for dealing with ports/sockets."""
from __future__ import annotations

import socket
import time
from typing import Union

from .exceptions import PortNotInUseError
from .exceptions import PortUnavailableError


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if port is in use.

    Obtained directly from https://stackoverflow.com/questions/2470971/fast-way-to-test-if-a-port-is-in-use-using-python
    Not unit tested...not sure best way how. But other methods call it.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
        return temp_socket.connect_ex((host, port)) == 0


def _confirm_port_availability(
    expected_to_be_available: bool,
    port: int,
    host: str = "127.0.0.1",
    timeout: Union[float, int] = 0,
) -> None:
    """Raise error if port not in expected state after timeout."""
    start_time = time.perf_counter()

    max_time = start_time + timeout
    while True:
        port_in_use = is_port_in_use(port, host=host)
        if not (port_in_use == expected_to_be_available):
            return
        current_time = time.perf_counter()
        if current_time > max_time:
            if expected_to_be_available:
                raise PortUnavailableError(
                    f"The port {host}:{port} was still unavailable even after waiting {timeout} seconds."
                )

            raise PortNotInUseError(
                f"The port {host}:{port} was still not in use even after waiting {timeout} seconds."
            )


def confirm_port_available(port: int, host: str = "127.0.0.1", timeout: Union[float, int] = 0) -> None:
    """Raise error if port unavailable after timeout.

    Args:
        port: the port number
        host: the host to check, defaults to 127.0.0.1
        timeout: the number in seconds to wait before raising an error. defaults to 0 which is no wait, must be immediately available
    """
    _confirm_port_availability(True, port, host=host, timeout=timeout)


def confirm_port_in_use(port: int, host: str = "127.0.0.1", timeout: Union[float, int] = 0) -> None:
    """Raise error if port is still open/unused after timeout.

    Args:
        port: the port number
        host: the host to check, defaults to 127.0.0.1
        timeout: the number in seconds to wait before raising an error. defaults to 0 which is no wait, must be already in use
    """
    _confirm_port_availability(False, port, host=host, timeout=timeout)
