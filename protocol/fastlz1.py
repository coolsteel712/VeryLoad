"""
Pure-Python port of the FastLZ level-1 encoder, translated line-by-line from
the reference fastlz.c (Ariya Hidayat, BSD license) vendored inside the
firmware's own fastlz_util.c toolchain (function names fastlz_compress_level /
fastlz_decompress match exactly). Only level 1 is ported (not level 2): the
firmware's own fastlz_decompress() auto-detects the encoding level from the
top 3 bits of the very first output byte, and a genuine level-1 stream always
naturally decodes as level 1, so level-1 output is fully valid input to the
real decompressor even though the firmware itself compresses with level 2.
Level 1 was chosen over level 2 for this port because its control flow has no
"far distance" extended-encoding edge cases, making a faithful, verifiable
translation far less error-prone.
"""
from __future__ import annotations

MAX_COPY = 32
MAX_LEN = 264  # 256 + 8
MAX_DISTANCE = 8192

HASH_LOG = 13
HASH_SIZE = 1 << HASH_LOG
HASH_MASK = HASH_SIZE - 1


def _readu16(buf: bytes, i: int) -> int:
    return buf[i] | (buf[i + 1] << 8)


def _hash(buf: bytes, i: int) -> int:
    v = _readu16(buf, i)
    v ^= _readu16(buf, i + 1) ^ (v >> (16 - HASH_LOG))
    return v & HASH_MASK


def fastlz1_compress(data: bytes) -> bytes:
    length = len(data)

    if length < 4:
        if length == 0:
            return b""
        out = bytearray()
        out.append(length - 1)
        out.extend(data)
        return bytes(out)

    ip = 0
    ip_bound = length - 2   # last index the tail-copy loop will include (after ip_bound++)
    ip_limit = length - 12  # main loop runs while ip < ip_limit

    htab = [0] * HASH_SIZE  # C inits every slot to point at the start of the buffer (index 0)
    out = bytearray()

    copy = 2
    out.append(MAX_COPY - 1)
    out.append(data[ip]); ip += 1
    out.append(data[ip]); ip += 1

    while ip < ip_limit:
        anchor = ip

        hval = _hash(data, ip)
        ref = htab[hval]
        distance = anchor - ref
        htab[hval] = anchor

        is_match = (
            distance != 0
            and distance < MAX_DISTANCE
            and data[ref] == data[ip]
            and data[ref + 1] == data[ip + 1]
            and data[ref + 2] == data[ip + 2]
        )

        if not is_match:
            out.append(data[anchor])
            ip = anchor + 1
            copy += 1
            if copy == MAX_COPY:
                copy = 0
                out.append(MAX_COPY - 1)
            continue

        # 3-byte match confirmed at ref..ref+2 == ip..ip+2 -- extend it.
        ip = anchor + 3
        r = ref + 3
        distance -= 1  # bias

        if distance == 0:
            x = data[ip - 1]
            while ip < ip_bound and data[r] == x:
                r += 1
                ip += 1
        else:
            # Mirrors `if(*ref++ != *ip++) break;` in C precisely: both
            # pointers advance EVEN on the byte that fails the comparison
            # (postfix increment is a side effect of evaluating the
            # expression, independent of the comparison's result). This "+1
            # overcount" whenever the match terminates via a genuine
            # mismatch is intentional -- it's exactly cancelled out by the
            # decoder's `len = (ctrl >> 5) - 1` bias below. Breaking without
            # that final increment (an earlier version of this port did)
            # desyncs encode/decode and corrupts the match length.
            all_eight_matched = True
            for _ in range(8):
                eq = data[r] == data[ip]
                r += 1
                ip += 1
                if not eq:
                    all_eight_matched = False
                    break
            if all_eight_matched:
                while ip < ip_bound:
                    eq = data[r] == data[ip]
                    r += 1
                    ip += 1
                    if not eq:
                        break

        # finalize the pending literal run's length byte
        if copy:
            out[len(out) - copy - 1] = copy - 1
        else:
            out.pop()
        copy = 0

        ip -= 3
        len_ = ip - anchor  # biased: 0 means a 3-byte match

        if len_ > MAX_LEN - 2:
            while len_ > MAX_LEN - 2:
                out.append((7 << 5) | (distance >> 8))
                out.append(MAX_LEN - 2 - 7 - 2)
                out.append(distance & 255)
                len_ -= (MAX_LEN - 2)

        if len_ < 7:
            out.append((len_ << 5) | (distance >> 8))
            out.append(distance & 255)
        else:
            out.append((7 << 5) | (distance >> 8))
            out.append(len_ - 7)
            out.append(distance & 255)

        hval = _hash(data, ip)
        htab[hval] = ip
        ip += 1
        hval = _hash(data, ip)
        htab[hval] = ip
        ip += 1

        out.append(MAX_COPY - 1)
        # 'copy' stays 0 here -- the byte just appended is a fresh placeholder

    ip_bound += 1  # C: ip_bound++ before the trailing literal-copy loop
    while ip <= ip_bound:
        out.append(data[ip])
        ip += 1
        copy += 1
        if copy == MAX_COPY:
            copy = 0
            out.append(MAX_COPY - 1)

    if copy:
        out[len(out) - copy - 1] = copy - 1
    else:
        out.pop()

    return bytes(out)
