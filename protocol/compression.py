"""
Pluggable compression backend for watch-face uploads.

docs/PROTOCOL_SPEC.md §6: the official app compresses every upload with
FastLZ before sending it (confirmed library name and ~62% ratio from the log),
using wire value ``compression_type=2``.

``FastLZCompressor`` (below) wraps a pure-Python port of the real reference
FastLZ level-1 encoder (protocol/fastlz1.py), validated byte-for-byte
identical to the actual compiled reference fastlz.c across ~470 test cases
including large (~600KB) payloads -- see that module's docstring for how it
was derived and verified. Encoding at level 1 rather than level 2 (which is
what the firmware itself uses when compressing data *to* the app) is
deliberate and safe: the real fastlz_decompress() auto-detects the encoding
level from the first output byte, and a genuine level-1 stream always
decodes correctly regardless of which level the *firmware's own* encoder
happens to use elsewhere.

The block-container framing (protocol/fastlz_block.py) mirrors the
firmware's own fastlz_util.c: fixed-size blocks, each individually
compressed and prefixed with a 4-byte big-endian compressed-length header,
with a split-into-two fallback for any block that fails to shrink. The block
size itself (default 4096) is NOT CONFIRMED -- fastlz_util.c takes it as a
parameter and the value actually passed isn't in the source available here.
4096 matches that same file's own DCOMPRESS_BUFFER_SIZE constant, making it
a reasonable default, but this should be confirmed against a real device (or
corrected) before relying on it in production -- if an upload with
compression_type=2 is rejected or corrupts the watch face, this is the first
thing to check.

``NullCompressor`` remains the default and is left in place: it's simpler
and it's still worth keeping around for protocol debugging (e.g. to rule out
compression as a variable when diagnosing an unrelated failure).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .constants import COMPRESSION_NONE, COMPRESSION_FASTLZ
from .fastlz_block import fastlz_block_compress, DEFAULT_COMPRESS_BLOCK_SIZE


@dataclass(frozen=True)
class CompressionResult:
    compressed_data: bytes
    compression_type: int


class Compressor(Protocol):
    """Implement this to plug in a real compressor (e.g. FastLZ)."""

    compression_type: int

    def compress(self, data: bytes) -> bytes:
        ...


class NullCompressor:
    """No compression. See module docstring -- kept as the default for now,
    and useful for isolating compression as a variable when debugging."""

    compression_type = COMPRESSION_NONE

    def compress(self, data: bytes) -> bytes:
        return data


class FastLZCompressor:
    """Real FastLZ compression, wire value 0x02. See module docstring for
    validation details and the one open unconfirmed parameter (block_size)."""

    compression_type = COMPRESSION_FASTLZ

    def __init__(self, block_size: int = DEFAULT_COMPRESS_BLOCK_SIZE) -> None:
        self.block_size = block_size

    def compress(self, data: bytes) -> bytes:
        return fastlz_block_compress(data, block_size=self.block_size)


def compress(data: bytes, compressor: Compressor | None = None) -> CompressionResult:
    backend = compressor or NullCompressor()
    return CompressionResult(
        compressed_data=backend.compress(data),
        compression_type=backend.compression_type,
    )
