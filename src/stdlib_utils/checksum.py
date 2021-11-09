# -*- coding: utf-8 -*-
"""Functions for calculating, embedding, and validating checksums."""
from __future__ import annotations

import struct
from typing import IO
from typing import Optional
from zlib import crc32

from .exceptions import Crc32ChecksumValidationFailureError
from .exceptions import Crc32InFileHeadDoesNotMatchExpectedValueError


def _convert_crc32_bytes_to_hex(checksum_bytes: bytes) -> str:
    checksum_int = struct.unpack(">I", checksum_bytes)[0]
    return ("%08X" % (checksum_int & 0xFFFFFFFF)).lower()


def compute_crc32_bytes_of_large_file(file_handle: IO[bytes], skip_first_n_bytes: int = 0) -> bytes:
    """Calculate the CRC32 checksum in a memory-efficient manner.

    Modified from: https://stackoverflow.com/questions/1742866/compute-crc-of-file-in-python

    Args:
        file_handle: the file handle to process. Should be opened in 'rb' mode
        skip_first_n_bytes: For cases when a checksum has been written in as the first bytes of a file (e.g. in an H5 userblock), the calculation can skip those bytes

    Returns:
        The CRC32 checksum as bytes
    """
    checksum = 0
    if skip_first_n_bytes > 0:
        file_handle.read(skip_first_n_bytes)
    while True:
        itered_bytes = file_handle.read(65536)
        if not itered_bytes:
            break
        checksum = crc32(itered_bytes, checksum)
    return struct.pack(">I", checksum)


def compute_crc32_hex_of_large_file(file_handle: IO[bytes], skip_first_n_bytes: int = 0) -> str:
    """Calcuates the lowercase zero-padded hex string of a file."""
    checksum_bytes = compute_crc32_bytes_of_large_file(file_handle, skip_first_n_bytes=skip_first_n_bytes)
    return _convert_crc32_bytes_to_hex(checksum_bytes)


def compute_crc32_and_write_to_file_head(  # pylint: disable=invalid-name # Eli (7/29/20): it's one character over the limit, but I can't think of a shorter way to describe it
    file_handle: IO[bytes],
) -> None:
    """Write the calculated CRC32 checksum over the first 4 bytes of the file.

    This is often used to facilitate encoding a CRC32 checksum in the Userblock of an H5 file.

    Args:
        file_handle: the file should be opened in 'rb+' mode
    """
    checksum_bytes = compute_crc32_bytes_of_large_file(file_handle, skip_first_n_bytes=4)
    file_handle.seek(0)
    file_handle.write(checksum_bytes)


def validate_file_head_crc32(file_handle: IO[bytes], expected_checksum: Optional[str] = None) -> None:
    """Validate a file where the CRC32 checksum is contained in the head.

    This is often used to facilitate encoding a CRC32 checksum in the Userblock of an H5 file.

    Raises error if mismatch in checksum detected or if supplied expected checksum does not match the value found at the file head.

    Args:
        file_handle: the file should be opened in 'rb' mode
        expected_checksum: If the expected checksum is already known (from records), then this can optionally be supplied to confirm the embedded checksum in the file head matches this.
    """
    checksum_bytes_in_file_head = file_handle.read(4)
    checksum_hex_in_file_head = _convert_crc32_bytes_to_hex(checksum_bytes_in_file_head)
    if expected_checksum is not None:
        if checksum_hex_in_file_head != expected_checksum:
            raise Crc32InFileHeadDoesNotMatchExpectedValueError(
                f"The expected checksum passed in to the function was {expected_checksum}, but the checksum found at the file head is {checksum_hex_in_file_head}."
            )

    actual_checksum_bytes = compute_crc32_bytes_of_large_file(file_handle)
    if actual_checksum_bytes != checksum_bytes_in_file_head:
        actual_checksum_hex = _convert_crc32_bytes_to_hex(actual_checksum_bytes)
        raise Crc32ChecksumValidationFailureError(
            f"The checksum calculated from the file was {actual_checksum_hex}, but the checksum found at the file head is {checksum_hex_in_file_head}."
        )
