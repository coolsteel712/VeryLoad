"""
High-level orchestrator implementing the full upload sequence from
docs/PROTOCOL_SPEC.md §5.4:

    1. D1 SET_FILE_INFO
    2. D1 START_TRANSFER
    3. D1 SET_BATCH_SIZE
    4. stream raw file bytes
    5. D1 END_TRANSFER (checksum)
    6. V3 APPLY_WATCHFACE

Public surface matches the shape requested for this project:

    uploader = WatchFaceUploader()
    devices = await uploader.scan()
    await uploader.connect(devices[0])
    await uploader.upload(path_to_iwf, on_progress=..., on_log=...)
    await uploader.disconnect()
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from bleak.backends.device import BLEDevice

from ble.transport import BLETransport, TransportError
from ble.transfer_session import stream_file_data
from errors import (
    AckTimeoutError,
    ConnectionFailedError,
    InvalidWatchFaceFileError,
    ProtocolAckError,
    RetryLimitExceededError,
    ScanTimeoutError,
)
from protocol import data_transfer as d1
from protocol import v3_frame
from protocol.checksum import compute_checksum
from protocol.compression import Compressor, FastLZCompressor, compress
from protocol.constants import (
    APPLY_WATCHFACE_NAME_FIELD_SIZE,
    CMD_APPLY_WATCHFACE,
    D1_OPCODE,
    D1_SET_FILE_INFO,
    D1_START_TRANSFER,
    D1_SET_BATCH_SIZE,
    D1_END_TRANSFER,
    DEFAULT_BATCH_SIZE,
    V3_PREFIX,
)
from protocol.data_transfer import D1Error

_D1_PREFIX = bytes([D1_OPCODE])
_V3_PREFIX = bytes([V3_PREFIX])
_SET_FILE_INFO_PREFIX = bytes([D1_OPCODE, D1_SET_FILE_INFO])
_START_TRANSFER_PREFIX = bytes([D1_OPCODE, D1_START_TRANSFER])
_SET_BATCH_SIZE_PREFIX = bytes([D1_OPCODE, D1_SET_BATCH_SIZE])
_END_TRANSFER_PREFIX = bytes([D1_OPCODE, D1_END_TRANSFER])

logger = logging.getLogger("veryfit_sideloader.uploader")

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, int], None]  # bytes_sent, total_bytes


@dataclass
class UploadResult:
    filename_on_watch: str
    original_size: int
    sent_size: int
    compression_type: int


class WatchFaceUploader:
    """See module docstring for the intended usage pattern."""

    def __init__(self, max_retries: int = 3, ack_timeout: float = 5.0) -> None:
        self._transport = BLETransport()
        self._max_retries = max_retries
        self._ack_timeout = ack_timeout
        self._nseq = 0x01  # V3 sequence counter; increments monotonically per session

    # -- public API ---------------------------------------------------------
    async def scan(self, timeout: float = 6.0) -> list[BLEDevice]:
        devices = await BLETransport.scan(timeout=timeout)
        if not devices:
            raise ScanTimeoutError(f"No BLE devices found in {timeout}s")
        return devices

    async def connect(self, device: BLEDevice) -> None:
        try:
            await self._transport.connect(device)
        except TransportError as exc:
            raise ConnectionFailedError(str(exc)) from exc

    async def disconnect(self) -> None:
        await self._transport.disconnect()

    async def upload(
        self,
        path: str | Path,
        compressor: Optional[Compressor] = FastLZCompressor(),
        batch_size: int = DEFAULT_BATCH_SIZE,
        on_progress: Optional[ProgressCallback] = None,
        on_log: Optional[LogCallback] = None,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> UploadResult:
        def log(msg: str) -> None:
            logger.info(msg)
            if on_log:
                on_log(msg)

        path = Path(path)
        if not path.is_file() or path.stat().st_size == 0:
            raise InvalidWatchFaceFileError(f"Not a valid file: {path}")

        original_data = path.read_bytes()
        original_size = len(original_data)
        log(f"Read {path.name} ({original_size} bytes)")

        result = compress(original_data, compressor=compressor)
        compressed_data = result.compressed_data
        compression_type = result.compression_type

        # File wire name includes .lz suffix if compressed
        transfer_filename = (
            f"{path.name}.lz" if compression_type != 0 else path.name
        )
        # Name used for APPLY_WATCHFACE retains file extension but drops .lz
        watchface_name = path.name

        log(
            f"Compression type={compression_type}, "
            f"{original_size} -> {len(compressed_data)} bytes"
        )

        await self._retry(
            "SET_FILE_INFO",
            log,
            self._do_set_file_info,
            original_size,
            compression_type,
            transfer_filename,
        )
        await self._retry(
            "START_TRANSFER",
            log,
            self._do_start_transfer,
            len(compressed_data),
            compression_type,
            transfer_filename,
        )
        await self._retry("SET_BATCH_SIZE", log, self._do_set_batch_size, batch_size)

        log(f"Uploading {len(compressed_data)} bytes...")
        stats = await stream_file_data(
            self._transport,
            compressed_data,
            batch_size=batch_size,
            on_progress=on_progress,
            cancel_event=cancel_event,
        )
        log(
            f"Sent {stats.total_packets} packets "
            f"({stats.packet_payload_size} bytes each, "
            f"last batch {stats.last_batch_packet_count} packets / "
            f"{stats.last_packet_length} bytes)"
        )

        checksum = compute_checksum(compressed_data)
        await self._retry("END_TRANSFER", log, self._do_end_transfer, checksum)
        log("Transfer verified by watch.")

        await self._retry(
            "APPLY_WATCHFACE", log, self._do_apply_watchface, watchface_name
        )
        log(f"Applied watch face: {watchface_name}")

        return UploadResult(
            filename_on_watch=watchface_name,
            original_size=original_size,
            sent_size=len(compressed_data),
            compression_type=compression_type,
        )

    # -- retry wrapper --------------------------------------------------------
    async def _retry(self, step_name: str, log: LogCallback, coro_fn, *args) -> None:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                await coro_fn(*args)
                return
            except (
                AckTimeoutError,
                ProtocolAckError,
                D1Error,
                v3_frame.FrameError,
            ) as exc:
                last_exc = exc
                log(f"{step_name} failed (attempt {attempt}/{self._max_retries}): {exc}")
                await asyncio.sleep(0.3 * attempt)
        raise RetryLimitExceededError(
            f"{step_name} failed after {self._max_retries} attempts"
        ) from last_exc

    # -- individual protocol steps --------------------------------------------
    async def _do_set_file_info(
        self, original_size: int, compression_type: int, filename: str
    ) -> None:
        await self._transport.write(
            d1.build_set_file_info(original_size, compression_type, filename)
        )
        ack = d1.parse_set_file_info_ack(await self._await_ack(_SET_FILE_INFO_PREFIX))
        if not ack.ok:
            raise ProtocolAckError(f"SET_FILE_INFO status={ack.status}")

    async def _do_start_transfer(
        self, compressed_size: int, compression_type: int, filename: str
    ) -> None:
        await self._transport.write(
            d1.build_start_transfer(compressed_size, compression_type, filename)
        )
        ack = d1.parse_start_transfer_ack(await self._await_ack(_START_TRANSFER_PREFIX))
        if not ack.ok:
            raise ProtocolAckError(f"START_TRANSFER status={ack.status}")

    async def _do_set_batch_size(self, batch_size: int) -> None:
        await self._transport.write(d1.build_set_batch_size(batch_size))
        ack = d1.parse_set_batch_size_ack(await self._await_ack(_SET_BATCH_SIZE_PREFIX))
        if not ack.ok:
            raise ProtocolAckError(f"SET_BATCH_SIZE status={ack.status}")

    async def _do_end_transfer(self, checksum: int) -> None:
        await self._transport.write(d1.build_end_transfer(checksum))
        ack = d1.parse_end_transfer_ack(
            await self._await_ack(_END_TRANSFER_PREFIX, timeout=30.0)
        )
        if not ack.ok:
            raise ProtocolAckError(
                f"END_TRANSFER status={ack.status} (checksum rejected)"
            )

    async def _do_apply_watchface(self, watchface_name: str) -> None:
        self._nseq += 1
        name_field = watchface_name.encode("ascii").ljust(
            APPLY_WATCHFACE_NAME_FIELD_SIZE, b"\x00"
        )
        payload = bytes([0x01]) + name_field
        frame = v3_frame.V3Frame(
            cmd_id=CMD_APPLY_WATCHFACE, nseq=self._nseq, payload=payload
        ).encode()
        await self._transport.write(frame)
        raw = await self._await_ack(_V3_PREFIX)
        try:
            reply = v3_frame.V3Frame.decode(raw)
        except v3_frame.FrameError as exc:
            raise ProtocolAckError(f"APPLY_WATCHFACE ack invalid: {exc}") from exc
        if (
            reply.cmd_id != CMD_APPLY_WATCHFACE
            or not reply.payload
            or reply.payload[0] != 0x00
        ):
            raise ProtocolAckError(
                f"APPLY_WATCHFACE rejected: {reply.payload[:4].hex()}"
            )

    async def _await_ack(self, expect_prefix: Optional[bytes] = None, timeout: Optional[float] = None) -> bytes:
        try:
            return await self._transport.wait_notification(
                timeout=timeout if timeout is not None else self._ack_timeout,
               expect_prefix=expect_prefix,
            )
        except TransportError as exc:
            raise AckTimeoutError(str(exc)) from exc