"""
Streams the raw (post file-info/start-transfer) file bytes to the watch.

docs/PROTOCOL_SPEC.md §5.3: this is the one part of the protocol that is a
**reconstruction**, not a directly-observed parse — the capture's debug level
never logged the individual data-packet writes, only the four control frames
and periodic progress percentages. The reconstruction is isolated entirely in
this one module so it's easy to correct later if a capture showing the actual
per-packet bytes becomes available (see spec §7, gap #2).

Reconstruction used (arithmetic double-confirmed against the log's own
"last notice packet cout / last packet data length" numbers — see spec):
  - packet payload size = negotiated ATT MTU - 3
  - no extra header/sequence/offset byte is prepended to each packet
  - packets are sent in batches (default size from D1 SET_BATCH_SIZE, 10),
    with a short pacing delay between batches, and a progress callback after
    each batch
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from protocol.constants import (
    ATT_HEADER_OVERHEAD,
    BATCH_PACING_SECONDS,
    D1_OPCODE,
    D1_SEND_DATA,
    DATA_CHUNK_HEADER_SIZE,
)
from .transport import BLETransport

logger = logging.getLogger("veryfit_sideloader.transfer")

ProgressCallback = Callable[[int, int], None]  # (bytes_sent, total_bytes)


@dataclass
class TransferStats:
    total_bytes: int
    packet_payload_size: int
    total_packets: int
    last_batch_packet_count: int
    last_packet_length: int


async def stream_file_data(
    transport: BLETransport,
    data: bytes,
    batch_size: int,
    on_progress: Optional[ProgressCallback] = None,
    cancel_event: Optional[asyncio.Event] = None,
) -> TransferStats:
    """
    Sends ``data`` to the watch in reconstructed raw packets. Raises
    ``asyncio.CancelledError`` if ``cancel_event`` is set mid-transfer.
    """
    packet_size = transport.negotiated_mtu - ATT_HEADER_OVERHEAD - DATA_CHUNK_HEADER_SIZE
    logger.info("Negotiated MTU reported by transport: %d", transport.negotiated_mtu)
    if packet_size <= 0:
        raise ValueError(f"Invalid packet size derived from MTU={transport.negotiated_mtu}")

    packets = [data[i : i + packet_size] for i in range(0, len(data), packet_size)]
    total_packets = len(packets)
    bytes_sent = 0

    logger.info(
        "Streaming %d bytes as %d packets (%d bytes/packet, batch=%d)",
        len(data), total_packets, packet_size, batch_size,
    )

    for batch_start in range(0, total_packets, batch_size):
        if cancel_event is not None and cancel_event.is_set():
            raise asyncio.CancelledError("Upload cancelled by user")

        batch = packets[batch_start : batch_start + batch_size]
        for packet in batch:
            framed = bytes([D1_OPCODE, D1_SEND_DATA, 0x00]) + packet
            await transport.write(framed)
            bytes_sent += len(packet)

        if on_progress:
            on_progress(bytes_sent, len(data))

        # POSSIBLE pacing value — see constants.py; avoids flooding the link
        # faster than the real app was observed to.
        await asyncio.sleep(BATCH_PACING_SECONDS)

    last_batch_size = total_packets - ((total_packets // batch_size) * batch_size) or (
        batch_size if total_packets else 0
    )
    last_packet_len = len(packets[-1]) if packets else 0

    return TransferStats(
        total_bytes=len(data),
        packet_payload_size=packet_size,
        total_packets=total_packets,
        last_batch_packet_count=last_batch_size,
        last_packet_length=last_packet_len,
    )
