"""
CRC16/CCITT-FALSE — CONFIRMED algorithm used by the "V3" wrapped command frames.

Verified against 61 independent complete frames captured from the official app
(both TX and RX) with zero mismatches: poly=0x1021, init=0xFFFF, no input/output
reflection, xorout=0x0000, result appended little-endian.

Implemented from scratch (no external crc dependency needed at runtime) so the
library has no third-party requirement beyond bleak/PyQt6.
"""
from __future__ import annotations

_POLY = 0x1021
_INIT = 0xFFFF


def crc16_ccitt_false(data: bytes) -> int:
    """Compute CRC16/CCITT-FALSE over ``data``. Returns a 16-bit unsigned int."""
    crc = _INIT
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ _POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


def crc16_bytes_le(data: bytes) -> bytes:
    """CRC16/CCITT-FALSE of ``data``, packed as 2 little-endian bytes."""
    return crc16_ccitt_false(data).to_bytes(2, "little")
