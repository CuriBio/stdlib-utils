# -*- coding: utf-8 -*-
import pytest
from stdlib_utils import confirm_port_available
from stdlib_utils import confirm_port_in_use
from stdlib_utils import PortNotInUseError
from stdlib_utils import ports
from stdlib_utils import PortUnavailableError


@pytest.mark.timeout(2)
def test_confirm_port_available__returns_quickly_when_available_even_with_long_timeout():
    confirm_port_available(7654, timeout=10)


def test_confirm_port_available__raises_error_if_port_unavailable_immediately(mocker):
    mocker.patch.object(ports, "is_port_in_use", autospec=True, return_value=True)
    with pytest.raises(
        PortUnavailableError,
        match="127.0.0.1:7654 was still unavailable even after waiting 0 seconds",
    ):
        confirm_port_available(7654)


def test_confirm_port_available__passes_correct_args_to_is_port_in_use(mocker):
    mocked_in_use = mocker.patch.object(ports, "is_port_in_use", autospec=True, return_value=False)
    confirm_port_available(7765, host="testhost")
    mocked_in_use.assert_called_once_with(7765, host="testhost")


@pytest.mark.timeout(1)
def test_confirm_port_in_use__returns_quickly_when_unavailable_even_with_long_timeout(
    mocker,
):
    mocker.patch.object(ports, "is_port_in_use", autospec=True, return_value=True)
    confirm_port_in_use(7654, timeout=10)


def test_confirm_port_in_use__raises_error_if_port_not_in_use_immediately(mocker):
    mocker.patch.object(ports, "is_port_in_use", autospec=True, return_value=False)
    with pytest.raises(
        PortNotInUseError,
        match="testhost4:7667 was still not in use even after waiting 0 seconds",
    ):
        confirm_port_in_use(7667, host="testhost4")


def test_confirm_port_in_use__passes_correct_args_to_is_port_in_use(mocker):
    mocked_in_use = mocker.patch.object(ports, "is_port_in_use", autospec=True, return_value=True)
    confirm_port_in_use(7766, host="testhost2")
    mocked_in_use.assert_called_once_with(7766, host="testhost2")


@pytest.mark.timeout(1)
def test_confirm_port_in_use__returns_after_a_few_iterations_until_port_is_available(
    mocker,
):
    mocked_is_in_use = mocker.patch.object(
        ports, "is_port_in_use", autospec=True, side_effect=[False, False, False, True]
    )
    confirm_port_in_use(7654, timeout=10)
    assert mocked_is_in_use.call_count == 4
