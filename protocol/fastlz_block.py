"""
Block-container wrapper matching fastlz_util.c's fastlz_util_compress_file /
fastlz_util_compress_buff exactly: input is split into fixed-size blocks,
each block is FastLZ-compressed independently and prefixed with its own
4-byte big-endian compressed-length header, and any block whose compressed
form would exceed the block size is instead split into two equal halves,
each compressed and headered separately (mirrors the firmware's own
"if (cmprs_size > compress_block_size)" fallback path).

UNCONFIRMED: the actual compress_block_size the firmware uses is not defined
anywhere in the uploaded fastlz_util.c (it's a parameter to that function,
set by whatever calls it, which we don't have). DCOMPRESS_BUFFER_SIZE=4096
is defined for the decompression side of that same file, so 4096 is used
here as a LIKELY default -- but this needs confirming (or the firmware
source that calls fastlz_util_compress_file with its actual argument) before
relying on it for a real upload.
"""
from __future__ import annotations

import struct

from .fastlz1 import fastlz1_compress

DEFAULT_COMPRESS_BLOCK_SIZE = 4096  # LIKELY, not CONFIRMED -- see module docstring
BLOCK_HEADER_SIZE = 4


def fastlz_block_compress(data: bytes, block_size: int = DEFAULT_COMPRESS_BLOCK_SIZE) -> bytes:
    out = bytearray()
    for i in range(0, len(data), block_size):
        chunk = data[i:i + block_size]
        _compress_block(chunk, block_size, out)
    return bytes(out)


def _compress_block(chunk: bytes, block_size: int, out: bytearray) -> None:
    compressed = fastlz1_compress(chunk)
    if len(compressed) > block_size and len(chunk) > 1:
        # Mirrors fastlz_util.c's fallback: split this block into two equal
        # halves and compress/header each independently.
        half = len(chunk) // 2
        _compress_block(chunk[:half], block_size, out)
        _compress_block(chunk[half:], block_size, out)
        return
    out.extend(struct.pack(">I", len(compressed)))  # big-endian, matches fastlz_util.c
    out.extend(compressed)