# -*- coding: utf-8 -*-
import inspect
import os
import tempfile

import pytest
from stdlib_utils import BlankAbsoluteResourcePathError
from stdlib_utils import create_directory_if_not_exists
from stdlib_utils import get_current_file_abs_directory
from stdlib_utils import get_current_file_abs_path
from stdlib_utils import get_formatted_stack_trace
from stdlib_utils import is_system_windows
from stdlib_utils import misc
from stdlib_utils import print_exception
from stdlib_utils import resource_path
from stdlib_utils import sort_nested_dict

PATH_OF_CURRENT_FILE = os.path.dirname((inspect.stack()[0][1]))


def test_resource_path__returns_from_path_of_current_file_by_default():
    actual_path = resource_path("my_file")
    expected_path = os.path.join(PATH_OF_CURRENT_FILE, "my_file")
    assert actual_path == expected_path


def test_resource_path__returns_from_supplied_base_path_when_provided():
    expected_base = os.path.join("linux", "eli")
    actual_path = resource_path("my_file2", base_path=expected_base)
    expected_path = os.path.join(expected_base, "my_file2")
    assert actual_path == expected_path


def test_resource_path__returns_from_path_of_meipass_when_frozen(mocker):
    mocker.patch.object(misc, "is_frozen_as_exe", autospec=True, return_value=True)
    expected_base = os.path.join("root_dir", "sub_dir")
    mocker.patch.object(
        misc, "get_path_to_frozen_bundle", autospec=True, return_value=expected_base
    )
    actual_path = resource_path("my_file3")
    expected_path = os.path.join(expected_base, "my_file3")
    assert actual_path == expected_path


def test_resource_path__returns_from_path_of_meipass_when_frozen_even_when_base_path_supplied(
    mocker,
):
    mocker.patch.object(misc, "is_frozen_as_exe", autospec=True, return_value=True)
    expected_base = os.path.join("root_dir2", "sub_dir88")
    mocker.patch.object(
        misc, "get_path_to_frozen_bundle", autospec=True, return_value=expected_base
    )
    actual_path = resource_path("my_file4", base_path="somethingcrazy")
    expected_path = os.path.join(expected_base, "my_file4")
    assert actual_path == expected_path


def test_resource_path__raises_error_if_blank_absolute_path_supplied():
    with pytest.raises(BlankAbsoluteResourcePathError):
        resource_path("blah", "")


def test_is_system_windows__true_when_true(mocker):
    mocker.patch("os.name", "nt")
    assert is_system_windows() is True


def test_is_system_windows__false_when_linux(mocker):
    mocker.patch("os.name", "posix")
    assert is_system_windows() is False


def dummy_signal_handler(my_list, arg1, arg2):
    my_list[0] = True


# def test_raise_alarm_signal__raises_on_linux(mocker):
#     # Eli (1/9/20) can't really figure out how to mock this very well, so creating a funky call out to a dummy signal handler
#     mocker.patch.object(misc, "is_system_windows", autospec=True, return_value=False)

#     is_windows = is_system_windows()

#     a_list = [False]
#     if is_windows:
#         mocker.patch.object(signal, "setitimer", create=True)
#         mocker.patch.object(signal, "ITIMER_REAL", create=True)
#     else:
#         mocked_setitimer = mocker.spy(signal, "setitimer")
#         signal.signal(14, functools.partial(dummy_signal_handler, a_list))
#     raise_alarm_signal()
#     time.sleep(0.01)
#     if not is_windows:
#         # if the system is actually linux, make sure to check the live result
#         assert a_list[0] is True
#         # make sure it was done in a linux-compatible way
#         mocked_setitimer.assert_called_once()


# def test_raise_alarm_signal__raises_on_windows(mocker):
#     is_windows = is_system_windows()
#     # Eli (1/9/20) can't really figure out how to mock this very well, so creating a funky call out to a dummy signal handler
#     mocker.patch.object(misc, "is_system_windows", autospec=True, return_value=True)
#     if is_windows:
#         c_raise = ctypes.CDLL("ucrtbase")
#         mocked_c_raise = mocker.patch.object(c_raise, "raise", autospec=True)

#         def side_effect(*args):
#             return {"raise": mocked_c_raise}

#         mocked_cdll = mocker.patch.object(
#             ctypes, "CDLL", autospec=True, side_effect=side_effect()
#         )
#     else:
#         mocked_cdll = mocker.patch.object(
#             ctypes, "CDLL", autospec=True, return_value={"raise": lambda x: None}
#         )
#     raise_alarm_signal()
#     time.sleep(0.01)
#     if is_windows:
#         # make sure it was done in a windows-compatible way
#         mocked_cdll.assert_called_once_with("ucrtbase")
#         mocked_c_raise.assert_called_once_with(14)


def test_create_directory_if_not_exists__when_no_directory_present():
    with tempfile.TemporaryDirectory() as tmp_dir:
        the_dir = os.path.join(tmp_dir, "logs")
        create_directory_if_not_exists(the_dir)
        assert os.path.isdir(the_dir) is True


def test_create_directory_if_not_exists__when_directory_already_present():
    # would raise a FileExistsError if failing
    with tempfile.TemporaryDirectory() as tmp_dir:
        the_dir = os.path.join(tmp_dir, "logs")
        os.makedirs(the_dir)
        create_directory_if_not_exists(the_dir)
        assert os.path.isdir(the_dir) is True


def test_get_formatted_stack_trace():
    expected_error = ValueError("test message")
    the_err = None
    try:
        raise expected_error
    except ValueError as e:
        the_err = e
    actual_stack_trace = get_formatted_stack_trace(the_err)
    assert "raise expected_error" in actual_stack_trace


def test_print_error_message(mocker):
    e = ValueError("some wrong value")
    mocked_print = mocker.patch("builtins.print", autospec=True)
    print_exception(e, "297a25ec-ce3e-46bc-9cb5-58ac4048bbd5")
    assert mocked_print.call_count == 1
    actual_call_str = str(mocked_print.mock_calls[0])
    assert "This fatal error message is being printed" in actual_call_str
    assert "297a25ec-ce3e-46bc-9cb5-58ac4048bbd5" in actual_call_str
    assert "ValueError" in actual_call_str
    assert "some wrong value" in actual_call_str
    assert ", line" in actual_call_str


def test_get_current_file_abs_path():
    expected_to_contain = os.path.join("stdlib-utils", "tests", "test_misc.py")
    actual = get_current_file_abs_path()

    assert actual.endswith(expected_to_contain) is True

    # the actual beginning of the absolute path could vary system to system...so just make sure there is something in front of the known portion of the path
    minimum_length = len(expected_to_contain) + 1
    assert len(actual) > minimum_length


def test_get_current_file_abs_directory():
    expected_to_contain = os.path.join("stdlib-utils", "tests")
    actual = get_current_file_abs_directory()

    assert actual.endswith(expected_to_contain)

    # the actual beginning of the absolute path could vary system to system...so just make sure there is something in front of the known portion of the path
    minimum_length = len(expected_to_contain) + 1
    assert len(actual) > minimum_length


def test_sort_nested_dict__returns_correct_dict():
    test_dict = {
        2: {"A": 7, "Z": 0, "V": None},
        3: True,
        1: bytes(2),
    }
    actual = sort_nested_dict(test_dict)

    expected_outer_keys = [1, 2, 3]
    for i, outer_key in enumerate(list(actual.keys())):
        assert outer_key == expected_outer_keys[i]
    expected_inner_keys = ["A", "V", "Z"]
    for i, inner_key in enumerate(list(actual[2].keys())):
        assert inner_key == expected_inner_keys[i]
