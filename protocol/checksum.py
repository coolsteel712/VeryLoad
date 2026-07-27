"""
Checksum used in the D1 END_TRANSFER frame.

docs/PROTOCOL_SPEC.md §5.2 / §7: only the *numeric value* of this checksum was
confirmed against the capture (0x6F8FCC, matching the log's own
"check code:0x6F8FCC" line). The exact algorithm producing that value was
never independently verified because the original ``custom1.iwf.lz`` payload
bytes were not captured — only its length and this checksum were.

CRC32 (zlib's implementation, the most common choice for this kind of
end-to-end transfer check) is used here as the default and is clearly
isolated behind this one function so it can be swapped out in one place if a
future capture (with the actual file bytes) proves a different algorithm.
"""
from __future__ import annotations

import zlib


def compute_checksum(data: bytes) -> int:
    """POSSIBLE algorithm — CRC32 of the exact bytes streamed to the watch.

    Swap this implementation if/when a capture with known-good source bytes
    contradicts it (see docs/PROTOCOL_SPEC.md §7, gap #3).
    """
    return zlib.crc32(data) & 0xFFFFFFFF
