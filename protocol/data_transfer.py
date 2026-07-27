"""
The 0xD1 "data transfer" control-frame family used to upload a watch-face file.

docs/PROTOCOL_SPEC.md §5 — every field here is CONFIRMED against the captured
log unless the docstring says otherwise. This module only builds/parses the
four *control* frames (SET_FILE_INFO, START_TRANSFER, SET_BATCH_SIZE,
END_TRANSFER). The raw data packets themselves are handled by
``ble/transfer_session.py`` since their exact on-wire framing is a
reconstruction (spec §5.3), not a confirmed parse.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from .constants import (
    D1_OPCODE,
    D1_SET_FILE_INFO,
    D1_START_TRANSFER,
    D1_SET_BATCH_SIZE,
    D1_END_TRANSFER,
    D1_STATUS_OK,
)


class D1Error(Exception):
    """Raised when a D1 ack fails to parse or reports a non-OK status."""


@dataclass(frozen=True)
class D1Ack:
    sub_command: int
    status: int
    reply_payload: bytes

    @property
    def ok(self) -> bool:
        return self.status == D1_STATUS_OK


def _decode_ack(raw: bytes, expected_sub: int) -> D1Ack:
    if len(raw) < 3 or raw[0] != D1_OPCODE:
        raise D1Error(f"not a D1 ack: {raw.hex()}")
    sub_command, status = raw[1], raw[2]
    if sub_command != expected_sub:
        raise D1Error(f"D1 ack sub-command mismatch: expected {expected_sub:#x}, got {sub_command:#x}")
    return D1Ack(sub_command=sub_command, status=status, reply_payload=raw[3:])


def build_set_file_info(original_size: int, compression_type: int, filename: str) -> bytes:
    """
    docs §5.2 — declare the (uncompressed) file about to be uploaded.
    The 0xFF byte is a POSSIBLE slot/"any" sentinel; only that value has ever
    been observed, so it is hard-coded rather than exposed as a parameter.
    """
    return (
        bytes([D1_OPCODE, D1_SET_FILE_INFO, 0xFF])
        + struct.pack("<I", original_size)
        + bytes([compression_type])
        + filename.encode("ascii")
    )


def parse_set_file_info_ack(raw: bytes) -> D1Ack:
    return _decode_ack(raw, D1_SET_FILE_INFO)


def build_start_transfer(compressed_size: int, compression_type: int, filename: str) -> bytes:
    """docs §5.2 — begin the transfer, declaring the size that will actually be streamed."""
    return (
        bytes([D1_OPCODE, D1_START_TRANSFER, 0xFF])
        + struct.pack("<I", compressed_size)
        + bytes([compression_type])
        + filename.encode("ascii")
    )


def parse_start_transfer_ack(raw: bytes) -> D1Ack:
    return _decode_ack(raw, D1_START_TRANSFER)


def build_set_batch_size(batch_size: int) -> bytes:
    """docs §5.2 — negotiate how many raw packets are sent per progress batch."""
    if not (0 < batch_size <= 255):
        raise ValueError("batch_size must fit in a single byte (1-255)")
    return bytes([D1_OPCODE, D1_SET_BATCH_SIZE, batch_size])


def parse_set_batch_size_ack(raw: bytes) -> D1Ack:
    return _decode_ack(raw, D1_SET_BATCH_SIZE)


def build_end_transfer(checksum: int) -> bytes:
    """docs §5.2 — finalize the transfer with a checksum of the streamed payload.

    NOTE: the exact checksum algorithm is UNKNOWN (only its numeric value was
    confirmed in the capture). CRC32 is the current best guess and is used by
    default — see ``checksum.py``.
    """
    return bytes([D1_OPCODE, D1_END_TRANSFER]) + struct.pack("<I", checksum)


def parse_end_transfer_ack(raw: bytes) -> D1Ack:
    return _decode_ack(raw, D1_END_TRANSFER)
