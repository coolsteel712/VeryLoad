"""
Encode/decode for "V3" wrapped command frames.

Layout (docs/PROTOCOL_SPEC.md §4.1, CONFIRMED):

    Byte 0        0x33            constant prefix
    Bytes 1-4     DA AD DA AD     constant magic
    Byte 5        0x01            version
    Bytes 6-7     length  (u16 LE)   == total_frame_length - 3
    Bytes 8-9     cmd_id  (u16 LE)
    Bytes 10-11   nseq    (u16 LE)
    Bytes 12..N-2 payload
    Bytes N-1,N   CRC16/CCITT-FALSE over frame[1:-2], appended little-endian
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from .constants import V3_PREFIX, V3_MAGIC, V3_VERSION
from .crc import crc16_bytes_le, crc16_ccitt_false


class FrameError(Exception):
    """Raised when a received buffer fails structural or CRC validation."""


@dataclass(frozen=True)
class V3Frame:
    cmd_id: int
    nseq: int
    payload: bytes = b""

    def encode(self) -> bytes:
        body = struct.pack("<HH", self.cmd_id, self.nseq) + self.payload
        header_len = 1 + len(V3_MAGIC) + 1  # prefix + magic + version
        length_field_len = 2
        crc_len = 2
        total = header_len + length_field_len + len(body) + crc_len
        length_value = total - 3  # CONFIRMED empirical formula, see spec §4.1

        frame = (
            bytes([V3_PREFIX])
            + V3_MAGIC
            + bytes([V3_VERSION])
            + struct.pack("<H", length_value)
            + body
        )
        frame += crc16_bytes_le(frame[1:])
        return frame

    @staticmethod
    def decode(data: bytes) -> "V3Frame":
        expected_prefix_magic_ver = bytes([V3_PREFIX]) + V3_MAGIC + bytes([V3_VERSION])
        if not data.startswith(expected_prefix_magic_ver):
            raise FrameError(f"not a V3 frame (bad header): {data[:8].hex()}")
        if len(data) < 14:
            raise FrameError(f"V3 frame too short: {len(data)} bytes")

        length_value = struct.unpack_from("<H", data, 6)[0]
        expected_total = length_value + 3
        if expected_total != len(data):
            raise FrameError(
                f"V3 frame length mismatch (likely a fragment awaiting reassembly): "
                f"declared total={expected_total}, actual bytes={len(data)}"
            )

        crc_actual = data[-2:]
        crc_calc = crc16_bytes_le(data[1:-2])
        if crc_actual != crc_calc:
            raise FrameError(
                f"CRC mismatch: frame says {crc_actual.hex()}, computed {crc_calc.hex()}"
            )

        cmd_id, nseq = struct.unpack_from("<HH", data, 8)
        payload = data[12:-2]
        return V3Frame(cmd_id=cmd_id, nseq=nseq, payload=payload)

    @staticmethod
    def declared_total_length(partial: bytes) -> int | None:
        """
        Given the first fragment of a (possibly multi-notification) V3 frame,
        return the full frame length it declares, or None if not enough bytes
        have arrived yet to read the length field.
        """
        if len(partial) < 8:
            return None
        length_value = struct.unpack_from("<H", partial, 6)[0]
        return length_value + 3
