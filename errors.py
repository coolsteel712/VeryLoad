"""Exception hierarchy for the sideloader, so the GUI can branch on failure kind."""


class SideloaderError(Exception):
    """Base class for all sideloader errors."""


class ScanTimeoutError(SideloaderError):
    """No devices found within the scan window."""


class ConnectionFailedError(SideloaderError):
    """Could not establish or maintain a BLE connection."""


class UnsupportedDeviceError(SideloaderError):
    """Connected device does not expose a usable write/notify characteristic pair."""


class ProtocolAckError(SideloaderError):
    """A control frame ack reported a non-OK status, or failed to parse."""


class AckTimeoutError(SideloaderError):
    """No ack/notification arrived within the expected window."""


class RetryLimitExceededError(SideloaderError):
    """A step failed repeatedly and the retry budget was exhausted."""


class InvalidWatchFaceFileError(SideloaderError):
    """The selected .iwf file could not be read or is empty."""
