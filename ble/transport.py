"""
Thin async wrapper around ``bleak`` handling scan/connect/discover + the raw
write/notify plumbing every higher-level command in this library sits on top
of.

docs/PROTOCOL_SPEC.md §1: the write/notify characteristic UUIDs are UNKNOWN —
they were never present in the (app-layer-only) log this project reverse
engineered. Rather than hard-code a guessed UUID, ``discover_io_characteristics``
enumerates every service/characteristic on the connected device and picks the
best candidate pair by GATT *properties* (write or write-without-response,
paired with a notify/indicate characteristic), logging every candidate it saw
so a human can confirm/correct the choice for a specific watch model.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice

logger = logging.getLogger("veryfit_sideloader.ble")

NotifyCallback = Callable[[bytes], None]

# CONFIRMED against a real capture (2026-07-22 IDOBlueProtocol log, IDW26):
# the actual data-transfer service is the vendor service below, with write
# characteristics 0AF1/0AF6 and notify characteristics 0AF2/0AF7 inside it.
_VENDOR_SERVICE_UUID = "00000af0-0000-1000-8000-00805f9b34fb"

# Well-known 16-bit SIG service UUIDs (GAP, GATT, Device Information, Battery,
# etc.) that are never the watch-face data channel. Every BLE peripheral
# exposes these for stack bookkeeping, and some of them (e.g. GATT's Service
# Changed / 0x2A05) legitimately require bonding to subscribe to — which is
# why discovery previously misidentified one of these as the data channel and
# then failed with a pairing/Access-Denied error that had nothing to do with
# the real vendor characteristics.
_STANDARD_SERVICE_UUIDS = {
    "00001800-0000-1000-8000-00805f9b34fb",  # Generic Access
    "00001801-0000-1000-8000-00805f9b34fb",  # Generic Attribute
    "0000180a-0000-1000-8000-00805f9b34fb",  # Device Information
    "0000180f-0000-1000-8000-00805f9b34fb",  # Battery Service
}


class TransportError(Exception):
    """Raised for connection, discovery, or write/notify failures."""


@dataclass
class IOCharacteristics:
    write_uuid: str
    notify_uuid: str
    write_without_response: bool


class BLETransport:
    """
    Owns one BleakClient and knows how to find + use the watch-face upload
    write/notify characteristic pair. Does not know anything about the
    VeryFit protocol itself — see ``protocol/`` and ``uploader.py`` for that.
    """

    def __init__(self) -> None:
        self._client: Optional[BleakClient] = None
        self._io: Optional[IOCharacteristics] = None
        self._notify_queue: "asyncio.Queue[bytes]" = asyncio.Queue()

    # -- discovery -----------------------------------------------------
    @staticmethod
    async def scan(timeout: float = 6.0) -> list[BLEDevice]:
        logger.info("Scanning for BLE devices (%.1fs)...", timeout)
        devices = await BleakScanner.discover(timeout=timeout)
        logger.info("Found %d device(s)", len(devices))
        return devices

    # -- connection ------------------------------------------------------
    async def connect(self, device: BLEDevice) -> None:
        logger.info("Connecting to %s (%s)...", device.name or "unknown", device.address)
        client = BleakClient(device)
        await client.connect()
        if not client.is_connected:
            raise TransportError(f"Failed to connect to {device.address}")
        self._client = client
        logger.info("Connected.")

        self._io = self._discover_io_characteristics(client)
        logger.info(
            "Selected write=%s (write_without_response=%s) notify=%s",
            self._io.write_uuid, self._io.write_without_response, self._io.notify_uuid,
        )

        try:
            await client.start_notify(self._io.notify_uuid, self._on_notify)
        except Exception as exc:  # noqa: BLE001 - bleak raises backend-specific error types
            # On Windows (WinRT backend), "Access Denied" from start_notify almost
            # always means the peripheral requires BLE pairing/bonding at the OS
            # level before it will allow the CCCD write that enables notifications
            # - even when the characteristic itself doesn't look encrypted. This is
            # not something the app-layer capture could ever reveal (pairing is a
            # link-layer concern), so it's handled here as a fallback rather than
            # documented as a protocol field. LIKELY fix, not CONFIRMED to work on
            # every watch model - if it still fails after pairing, the device may
            # need to be paired manually via the OS Bluetooth settings first.
            logger.warning(
                "start_notify failed (%s); attempting to pair and retry once...", exc
            )
            try:
                paired = await client.pair()
                logger.info("Pair result: %s", paired)
            except Exception as pair_exc:  # noqa: BLE001
                logger.warning("Pairing attempt failed or unsupported: %s", pair_exc)
            try:
                await client.start_notify(self._io.notify_uuid, self._on_notify)
            except Exception as retry_exc:  # noqa: BLE001
                raise TransportError(
                    f"Could not enable notifications on {self._io.notify_uuid} "
                    f"even after attempting to pair: {retry_exc}. Try pairing the "
                    f"watch manually in your OS Bluetooth settings first, then "
                    f"reconnect."
                ) from retry_exc

    def _discover_io_characteristics(self, client: BleakClient) -> IOCharacteristics:
        """
        GATT discovery — see module docstring. Logs every candidate
        characteristic it finds (at INFO level) so a mismatch is easy to spot
        and correct for a new watch model. Standard SIG bookkeeping services
        (GAP/GATT/Device Info/Battery) are excluded from candidacy: they're
        never the data channel, and some of their characteristics (e.g. GATT's
        Service Changed) require bonding to subscribe to, which previously
        surfaced as a misleading pairing/Access-Denied failure.
        """
        write_candidates: list[BleakGATTCharacteristic] = []
        notify_candidates: list[BleakGATTCharacteristic] = []
        vendor_service_candidates: list[BleakGATTCharacteristic] = []

        for service in client.services:
            if service.uuid.lower() in _STANDARD_SERVICE_UUIDS:
                logger.info("Skipping standard SIG service: %s", service.uuid)
                continue
            for char in service.characteristics:
                props = set(char.properties)
                logger.info(
                    "GATT candidate: service=%s char=%s props=%s",
                    service.uuid, char.uuid, sorted(props),
                )
                if "write" in props or "write-without-response" in props:
                    write_candidates.append(char)
                if "notify" in props or "indicate" in props:
                    notify_candidates.append(char)
                if service.uuid.lower() == _VENDOR_SERVICE_UUID:
                    vendor_service_candidates.append(char)

        if not write_candidates or not notify_candidates:
            raise TransportError(
                "Could not find a write+notify characteristic pair on this device "
                "(after excluding standard GAP/GATT/Device-Info/Battery services). "
                "See the GATT candidate list above and update discovery logic for "
                "this watch model."
            )

        # Prefer the CONFIRMED vendor service (00000af0-...) if this device
        # exposes it, since that's the actual data-transfer service seen in a
        # real capture rather than a same-service heuristic guess.
        vendor_write = [c for c in vendor_service_candidates if c in write_candidates]
        vendor_notify = [c for c in vendor_service_candidates if c in notify_candidates]
        if vendor_write and vendor_notify:
            w, n = vendor_write[0], vendor_notify[0]
            return IOCharacteristics(
                write_uuid=w.uuid,
                notify_uuid=n.uuid,
                write_without_response="write-without-response" in w.properties,
            )

        # Prefer a pair that lives in the same service (common convention).
        for w in write_candidates:
            for n in notify_candidates:
                if w.service_uuid == n.service_uuid:
                    return IOCharacteristics(
                        write_uuid=w.uuid,
                        notify_uuid=n.uuid,
                        write_without_response="write-without-response" in w.properties,
                    )

        # Fall back to the first candidates found.
        w, n = write_candidates[0], notify_candidates[0]
        logger.warning(
            "No same-service write/notify pair found; falling back to first "
            "candidates of each kind. Verify this is correct for this watch model."
        )
        return IOCharacteristics(
            write_uuid=w.uuid,
            notify_uuid=n.uuid,
            write_without_response="write-without-response" in w.properties,
        )

    def _on_notify(self, _handle: int, data: bytearray) -> None:
        self._notify_queue.put_nowait(bytes(data))

    # -- io ---------------------------------------------------------------
    async def write(self, data: bytes) -> None:
        if not self._client or not self._io:
            raise TransportError("Not connected")
        await self._client.write_gatt_char(
            self._io.write_uuid, data, response=not self._io.write_without_response
        )

    async def wait_notification(self, timeout: float = 5.0, expect_prefix: Optional[bytes] = None) -> bytes:
        """
        Waits for a notification. If ``expect_prefix`` is given, notifications
        that don't start with it are discarded (logged at DEBUG) rather than
        returned — the watch's notify characteristic can carry a stale/cached
        value from a previous session (CONFIRMED: seen in a real capture as the
        0AF7 characteristic's leftover ``value`` field before subscription) as
        well as unsolicited pushes, interleaved with the actual ack a caller is
        waiting for. Without this filter the first queued item wins, which can
        hand a caller garbage instead of the reply it asked for.
        """
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise TransportError("Timed out waiting for a notification")
            try:
                data = await asyncio.wait_for(self._notify_queue.get(), timeout=remaining)
            except asyncio.TimeoutError as exc:
                raise TransportError("Timed out waiting for a notification") from exc
            if expect_prefix is None or data.startswith(expect_prefix):
                return data
            logger.debug("Discarding unexpected notification: %s", data.hex())

    @property
    def negotiated_mtu(self) -> int:
        """
        bleak exposes the negotiated ATT MTU after connection. Falls back to
        the CONFIRMED value from the capture (180) if unavailable.
        """
        if self._client is not None:
            mtu = getattr(self._client, "mtu_size", None)
            if mtu:
                return mtu
        from ..protocol.constants import DEFAULT_ATT_MTU
        return DEFAULT_ATT_MTU

    async def disconnect(self) -> None:
        if self._client and self._client.is_connected:
            logger.info("Disconnecting...")
            await self._client.disconnect()
        self._client = None
        self._io = None