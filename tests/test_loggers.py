# -*- coding: utf-8 -*-
import logging
import os
import sys
import tempfile
import time
from unittest.mock import ANY

from freezegun import freeze_time
import pytest
from stdlib_utils import configure_logging
from stdlib_utils import LogFolderDoesNotExistError
from stdlib_utils import LogFolderGivenWithoutFilePrefixError
from stdlib_utils import UnrecognizedLoggingFormatError


def test_configure_logging__default_args_sets_up_logging_on_stdout(mocker):
    spied_basic_config = mocker.spy(logging, "basicConfig")
    spied_stream_handler = mocker.spy(logging, "StreamHandler")
    configure_logging()

    assert (
        logging.Formatter.converter  # pylint: disable=comparison-with-callable
        == time.gmtime  # pylint: disable=comparison-with-callable
    )

    spied_stream_handler.assert_called_once_with(sys.stdout)
    assert spied_basic_config.call_count == 1
    _, kwargs = spied_basic_config.call_args_list[0]
    assert set(kwargs.keys()) == set(["level", "format", "handlers"])
    assert kwargs["level"] == logging.INFO
    assert (
        kwargs["format"]
        == "[%(asctime)s UTC] %(name)s-{%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
    )
    actual_handlers = kwargs["handlers"]
    assert len(actual_handlers) == 1

    # if pytest is automatically capturing stdout, then it does some adjustments to change the output, so the second or clause is needed
    assert actual_handlers[
        0
    ].stream.name == "<stdout>" or "_pytest.capture.EncodedFile" in str(
        type(actual_handlers[0].stream)
    )


def test_configure_logging__with_notebook_format(mocker):
    spied_basic_config = mocker.spy(logging, "basicConfig")
    configure_logging(logging_format="notebook")

    assert (
        logging.Formatter.converter  # pylint: disable=comparison-with-callable
        == time.gmtime  # pylint: disable=comparison-with-callable
    )

    assert spied_basic_config.call_count == 1
    _, kwargs = spied_basic_config.call_args_list[0]
    assert set(kwargs.keys()) == set(["level", "format", "handlers"])
    assert kwargs["level"] == logging.INFO
    assert kwargs["format"] == "[%(asctime)s UTC] %(levelname)s - %(message)s"
    actual_handlers = kwargs["handlers"]
    assert len(actual_handlers) == 1

    # if pytest is automatically capturing stdout, then it does some adjustments to change the output, so the second or clause is needed
    assert actual_handlers[
        0
    ].stream.name == "<stdout>" or "_pytest.capture.EncodedFile" in str(
        type(actual_handlers[0].stream)
    )


def test_configure_logging__raises_error_with_unrecognized_logging_format():
    test_format = "fake_format"
    with pytest.raises(UnrecognizedLoggingFormatError, match=test_format):
        configure_logging(logging_format=test_format)


def test_configure_logging__sets_log_level_to_provided_arg(mocker):
    spied_basic_config = mocker.spy(logging, "basicConfig")
    configure_logging(log_level=logging.DEBUG)
    spied_basic_config.assert_called_once_with(
        level=logging.DEBUG, format=ANY, handlers=ANY
    )


@freeze_time("2020-07-15 10:35:08")
def test_configure_logging__with_path_to_log_folder_and_file_name__uses_path_as_logging_folder__and_does_not_use_stdout(
    mocker,
):
    with tempfile.TemporaryDirectory() as tmp_dir:
        mocked_basic_config = mocker.patch.object(logging, "basicConfig")
        configure_logging(log_file_prefix="my_log", path_to_log_folder=tmp_dir)

        # spied_stream_handler.assert_not_called()
        assert mocked_basic_config.call_count == 1
        _, kwargs = mocked_basic_config.call_args_list[0]
        assert set(kwargs.keys()) == set(["level", "format", "handlers"])

        actual_handlers = kwargs["handlers"]
        assert len(actual_handlers) == 1
        file_handler = actual_handlers[0]
        assert isinstance(file_handler, logging.FileHandler) is True
        assert file_handler.baseFilename == os.path.join(
            tmp_dir, "my_log__2020_07_15_103508.txt"
        )
        # Tanner (8/7/20): windows raises error if file is not closed
        file_handler.close()


def test_configure_logging__sets_formatter_on_all_handlers_if_given(mocker):
    class TestFormatter(logging.Formatter):
        pass

    test_formatter = TestFormatter()
    with tempfile.TemporaryDirectory() as tmp_dir:
        spied_basic_config = mocker.patch.object(logging, "basicConfig")
        configure_logging(
            log_file_prefix="my_log",
            path_to_log_folder=tmp_dir,
            logging_formatter=test_formatter,
        )
        assert spied_basic_config.call_count == 1

        actual_handlers = spied_basic_config.call_args_list[0][1]["handlers"]
        assert len(actual_handlers) > 0
        for i, handler in enumerate(actual_handlers):
            assert isinstance(handler.formatter, TestFormatter), i

        # Tanner (8/7/20): windows raises error if file is not closed
        file_handler = actual_handlers[0]
        file_handler.close()


def test_configure_logging__raises_error_if_path_to_folder_does_not_exist(mocker):
    test_folder = "fake_folder"
    with pytest.raises(LogFolderDoesNotExistError, match=test_folder):
        configure_logging(log_file_prefix="my_log", path_to_log_folder=test_folder)


def test_configure_logging__raises_error_if_path_to_folder_given_without_file_name(
    mocker,
):
    with pytest.raises(LogFolderGivenWithoutFilePrefixError):
        configure_logging(path_to_log_folder="dir")
