"""
Protocol constants for the VeryFit / IDO "protocol V3" family.

Every constant is annotated with its confidence tag from docs/PROTOCOL_SPEC.md.
Only what the sideloader actually needs is defined here — the log contains many
other opcodes (device info, battery, heart rate, notifications, etc.) that are
out of scope for a watch-face-only uploader and are intentionally omitted
rather than guessed at.
"""

# --- V3 wrapped-frame constants (docs/PROTOCOL_SPEC.md §4) --------------- CONFIRMED
V3_PREFIX = 0x33
V3_MAGIC = bytes.fromhex("DAADDAAD")
V3_VERSION = 0x01

# V3 command ids relevant to watch-face upload             --------------- CONFIRMED
CMD_GET_WATCHFACE_LIST = 0x31
CMD_APPLY_WATCHFACE = 0x08

# APPLY_WATCHFACE payload = 1 flag byte + a fixed-width, zero-padded ASCII
# filename field. CONFIRMED width from the capture: total payload was 31
# bytes for an 11-byte name ("custom1.iwf"), i.e. a 30-byte name field.
APPLY_WATCHFACE_NAME_FIELD_SIZE = 30

# --- Simple 2-byte "V1" administrative commands (§3) --------------------
OPCODE_GET_MTU_INFO = (0x02, 0xF0)  # CONFIRMED: request/response pair for MTU query

# --- File-transfer ("D1") command family (§5) ---------------------------- CONFIRMED
D1_OPCODE = 0xD1
D1_SET_FILE_INFO = 0x08
D1_START_TRANSFER = 0x01
D1_SET_BATCH_SIZE = 0x05
D1_END_TRANSFER = 0x03
D1_SEND_DATA = 0x02          # <-- ADD: real-capture-confirmed, wraps every raw data packet
DATA_CHUNK_HEADER_SIZE = 3    # <-- ADD: 0xD1 + sub-command + reserved byte, prepended to every data packet

D1_STATUS_OK = 0x00  # only value ever observed; other codes are UNKNOWN

# --- Compression -----------------------------------------------------------
COMPRESSION_NONE = 0x00      # UNKNOWN whether firmware accepts this — not observed in capture
COMPRESSION_FASTLZ = 0x02    # LIKELY meaning of the observed value; library name CONFIRMED

# --- Transfer tuning (from §5.3, LIKELY reconstruction, not directly observed) ---
DEFAULT_BATCH_SIZE = 10          # LIKELY, confirmed via D1 05 negotiation + arithmetic
DEFAULT_ATT_MTU = 180            # CONFIRMED (protocol_set_mtu tx:180 rx:180)
ATT_HEADER_OVERHEAD = 3           # standard BLE ATT write header overhead
BATCH_PACING_SECONDS = 0.15       # POSSIBLE — approximate pacing observed between batches in log
