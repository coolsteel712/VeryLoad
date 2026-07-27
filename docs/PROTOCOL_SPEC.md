# VeryFit / IDO BLE Watch Face Upload Protocol — Reverse-Engineering Spec

**Source evidence:** `2026-07-21.txt` — an internal debug log from the official VeryFit-family
iOS app (`clib` logging layer, source files `protocol.c`, `protocol_v3.c`, `protocol_v3_queue.c`,
`data_tran.c`, `mkWatchFace.cpp`, `fastlz_util.c`). It captures every app-layer `TX`/`RX` byte
buffer during a real watch-face upload (`custom1.iwf` → `custom1.iwf.lz`) to an IDO-protocol-V3
watch, plus companion `.iwf` (`f283.iwf`) and OTA firmware (`idw26_ota_V1.00.14_20260211.fw`)
files.

Every field below is tagged:
- **CONFIRMED** — directly observed and cross-checked against explicit log values (e.g. the app
  prints `original_size:228205` and the byte-for-byte TX frame contains `6D 7B 03 00` = 228205 LE).
- **LIKELY** — derived by consistent arithmetic/pattern across many frames, not seen as an explicit
  log statement.
- **POSSIBLE** — a plausible reading that fits the evidence but has only one or zero independent
  confirmations.
- **UNKNOWN** — not present in this evidence at all; flagged rather than guessed.

This log is an **application-layer** capture (above the GATT layer) — it shows exactly what bytes
were written to / read from the watch's characteristic(s), but not the BLE service/characteristic
**UUIDs** themselves, and not link-layer detail (connection intervals, PHY, etc.).

---

## 1. Connection / GATT layer

| Item | Status | Notes |
|---|---|---|
| Service UUID | **UNKNOWN** | Not present in this log (app-layer only). Must be discovered live via GATT enumeration against a real device. |
| Write characteristic UUID | **UNKNOWN** | Same as above. |
| Notify characteristic UUID | **UNKNOWN** | Same as above. |
| Transport | **LIKELY** | Write + Notify pair (single bidirectional pipe multiplexing every command family below — 2-byte "GET" commands, `0x33`-wrapped "V3" commands, and `0xD1` file-transfer commands all share the same TX/RX log stream). |

**Do not guess the UUIDs.** The uploader below performs live service/characteristic discovery
and selects candidates by GATT *properties* (write / write-without-response + notify), logging
every candidate so a human can confirm the right pair for a specific watch model on first run.

---

## 2. MTU negotiation

CONFIRMED from log:
```
TX : 02 F0
RX : 02 F0 00 B4 00 B4 00 00 00 B7 00 00 00 00 00 00 00 00 00 00
[protocol.c] [protocol_set_mtu] [line 800] set mtu tx:180 rx:180
```
- `02 F0` = simple 2-byte "GET_MTU_INFO" request (opcode `0x02`, sub-id `0xF0`).
- Response byte layout: `00` (status) `B4 00` (tx mtu = 0x00B4 = **180**, LE u16) `B4 00` (rx mtu =
  180, LE u16) `00 00` `B7 00` (0x00B7 = 183 — **POSSIBLE**: a secondary/negotiated ATT MTU value)
  then zero padding to a fixed 20-byte reply buffer.
- **CONFIRMED**: final application MTU = **180 bytes** (both directions), observed identically at
  two separate points in the log (`protocol_set_mtu ... tx:180 rx:180`).
- Every `RX`/`TX` line elsewhere in the log that is *not* an `0x33`-wrapped "V3" frame is a fixed
  20-byte buffer (zero-padded) — this is a debug-print artifact of the app's fixed-size receive
  buffer, not evidence that 20 bytes is a protocol constant.
- Large "V3" (`0x33`-prefixed) frames are seen split across **multiple physical notifications of
  up to 180 bytes each** (i.e. the ATT_MTU value), reassembled by the app before being logged as
  one complete frame. This was confirmed by finding "orphan" fragments in the log whose declared
  `length` field exceeds what the fragment itself contains (see §4).

---

## 3. Base ("V1") simple command frames

Short administrative commands (device MAC, function tables, notice status, connection
parameters, battery, MTU) use a minimal 2-byte-header form:

```
Byte 0   Opcode / command class
Byte 1   Sub-command / field id
[Bytes 2+  optional request payload]
```//
Example — device MAC:
```
TX : 02 04
RX : 02 04 F4 F5 35 AA 7F 98 F4 F5 35 AA 7F 98 00 00 00 00 00 00
```
Responses are logged as fixed 20-byte buffers: `opcode, sub-id, ...payload..., zero padding`.

**Status: CONFIRMED** as a class of frames exists and is used for non-file traffic; the specific
meaning of every opcode/sub-id pair in this family (0x02, 0x03, 0x04, 0x06, 0x07, 0x13, …) is
**out of scope** for the sideloader and not fully catalogued here — only the two that matter for
watch-face upload are documented (MTU query above; everything else the sideloader needs is in
§4/§5).

---

## 4. "V3" wrapped command frames (used for watch-face **list** and **apply**)

### 4.1 Frame layout — CONFIRMED

```
Byte 0        0x33                       constant frame marker
Bytes 1-4     DA AD DA AD                constant magic
Byte 5        0x01                       protocol version
Bytes 6-7     length            (u16 LE) see formula below
Bytes 8-9     cmd_id            (u16 LE)
Bytes 10-11   nseq              (u16 LE) monotonically-incrementing per-command sequence number
Bytes 12..N-2 payload            (variable)
Bytes N-1,N   CRC16             (u16 LE) see §4.3
```

**Length field formula — CONFIRMED** (verified against 61 complete, unfragmented V3 frames with
zero mismatches):
```
length = total_frame_length_in_bytes - 3
```
i.e. `length` is "everything in the frame except the leading `0x33` byte and the trailing 2-byte
CRC's… " — empirically it is simply `total-3`; we can prove the arithmetic but the app's internal
rationale for the constant `3` is **POSSIBLE** (most likely: the 3-byte outer ATT header the
transport layer will prepend before wire-transmission, budgeted for symmetrically by the app —
not provable from this evidence alone).

Fragmentation: when a V3 frame's `length` implies more bytes than fit in one 180-byte MTU chunk,
the device (or app) splits it across consecutive raw notifications; the app reassembles by byte
count before re-logging the frame whole. Individual fragment boundaries are **not** separately
tagged in-band (no fragment index/offset byte observed) — reassembly relies purely on the
already-known target length from the frame header of the *first* fragment.

### 4.2 CRC16 — CONFIRMED

```python
crc = crc16_ccitt_false(frame[1:-2])   # poly 0x1021, init 0xFFFF, no reflect, xorout 0x0000
frame_crc_bytes = crc.to_bytes(2, "little")
```
Verified against every complete V3 frame in the log (61/61 match, including both TX and RX,
including the exact "apply watch face" frame in §5.2) with **zero exceptions** using
`crcmod.predefined.mkCrcFun('crc-ccitt-false')`.

### 4.3 Commands relevant to watch-face upload

| cmd_id | Name | Direction | Notes |
|---|---|---|---|
| `0x31` | GET_WATCHFACE_LIST | TX (empty payload) / RX (array of entries) | CONFIRMED. Returns existing installed watch faces: repeating records of `flags(1) type(1) unknown(1) checksum(u32 LE) size(u32 LE) filename(ascii, zero-padded to fixed width)`. Useful for showing "installed dials" / free-slot info in the GUI; not required to *perform* an upload. |
| `0x08` | APPLY_WATCHFACE (a.k.a. "set current dial") | TX / RX ack | **CONFIRMED**, see §5.2. Sent immediately after a successful file-transfer completion (`D1 03` ack), naming the just-uploaded file (without its `.lz` suffix) to make the watch switch to it. |

Both use `nseq` values that increment across the whole session (shared counter across command
families) — CONFIRMED from the log (`nseq=0x27` → `0x28` → `0x29` → `0x2A` → `0x2B` in sequence
across `0x31` and `0x08` commands, interleaved).

---

## 5. File-transfer sub-protocol (`0xD1` command family) — the actual upload

This is the protocol the sideloader must implement. It does **not** use the V3 wrapper — it's a
simpler, unwrapped frame form, confirmed byte-for-byte against the log's own printed metadata
(file name, sizes, compression type, checksum all match exactly).

### 5.1 Frame layout — CONFIRMED

Request:
```
Byte 0      0xD1        constant "data transfer" opcode
Byte 1      sub-command  (see table)
Bytes 2+    sub-command-specific payload
```
Response (fixed 20-byte buffer, zero-padded):
```
Byte 0      0xD1        echoed opcode
Byte 1      sub-command  echoed
Byte 2      status       (0x00 = success; CONFIRMED for every ack in this capture — no failure
                           case observed, so non-zero status meaning is UNKNOWN)
Bytes 3+    sub-command-specific reply payload, then zero padding
```

### 5.2 Sub-commands — CONFIRMED byte-for-byte against this capture

**`0x08` — SET_FILE_INFO** (declare the file about to be sent):
```
TX: D1 08 FF <original_size:u32 LE> <compression_type:u8> <filename: ascii, no NUL padding>
RX: D1 08 <status:u8> <max_name_len_or_param:u16 LE> 00...00
```
Observed: `D1 08 FF 6D7B0300 02 "custom1.iwf.lz"`
- `original_size` = 228205 = the **uncompressed** `.iwf` file size — CONFIRMED equal to the log's
  own `original_size:228205` statement.
- `compression_type` = `0x02` — CONFIRMED equal to log's `compression_type:2`. (`fastlz_util.c`
  is invoked immediately before this to compress the file — **LIKELY** `2` = FastLZ.)
- `filename` = the **compressed** filename including the app-added `.lz` suffix.
- The `0xFF` byte's meaning is **POSSIBLE** — a "slot id" or "any slot" sentinel; not otherwise
  exercised in this capture (only one upload observed).
- Ack's `0x0032` (=50) value — **POSSIBLE**: a maximum filename length or similar limit echoed by
  the watch; not confirmed by any other reference in the log.

**`0x01` — START_TRANSFER**:
```
TX: D1 01 FF <compressed_size:u32 LE> <compression_type:u8> <filename: ascii>
RX: D1 01 <status:u8> 00...00
```
Observed: `D1 01 FF 14560100 02 "custom1.iwf.lz"` — `14560100` LE = 87572 = **CONFIRMED** equal to
log's `size:87572` (the **compressed** payload size that will actually be streamed).

**`0x05` — SET_BATCH_SIZE** (negotiate how many raw data packets are sent between progress
callbacks / acks):
```
TX: D1 05 <batch_size:u8>
RX: D1 05 <status:u8> <batch_size:u16 LE> 00...00
```
Observed: `D1 05 0A` → ack echoes `0A 00` (=10). **LIKELY** meaning: 10 raw write packets are sent
per "batch" before the app logs a progress update; corroborated arithmetically in §5.3.

**Raw data packets — UNCONFIRMED framing.** The log's debug level does not print the individual
file-content writes (only the 4 control commands above and periodic `notice_packet_completed`
progress percentages are logged). This is the single biggest gap in this reverse-engineering
pass — see §5.3 for the best-effort reconstruction and §7 for what evidence would close the gap.

**`0x03` — END_TRANSFER (verify)**:
```
TX: D1 03 <checksum:u32 LE>
RX: D1 03 <status:u8> 00...00
```
Observed: `D1 03 CC8F6F00` — CONFIRMED equal to `check code:0x6F8FCC` (LE u32, top byte 0x00).
Algorithm of this checksum is **UNKNOWN** (only its numeric value is confirmed, not how it's
computed — no reference source bytes for `custom1.iwf.lz` were captured to test against CRC32/
other candidates). **POSSIBLE**: CRC32 of the compressed payload, given the app's general
preference for CRC16/CRC32 elsewhere and the value's byte-width; not verified.

### 5.3 Raw data packet reconstruction — LIKELY (arithmetic reconstruction, not directly observed)

From the log:
```
[data_tran.c] [process_write_packet] send end,total send size:87572
    last notice packet cout:5 last packet data length:842
```
- Total compressed bytes sent: 87572 (matches START_TRANSFER's declared size).
- Progress percentage was reported ~50 times, close to evenly spaced (2%, 4%, 6%, …, 99%),
  consistent with **10 packets per batch** (from the `0x05` negotiation) × ~49 full batches + one
  final partial batch of **5** packets.
- If each full raw packet carries `ATT_MTU - 3` = `180 - 3` = **177 bytes** of file payload:
  `87572 / 177 ≈ 494.75` ⇒ **495 total packets** (494 full + 1 short final packet of 134 bytes).
  Grouped into batches of 10, that's 49 full batches (490 packets) + 1 final batch of **5**
  packets — which matches the log's own "last notice packet cout:5" exactly, and
  `4 × 177 + 134 = 842` matches the log's own "last packet data length:842" exactly.

This is strong (two independent numeric matches) but still **LIKELY, not CONFIRMED**, because the
per-packet framing itself was never logged. Best-effort reconstruction used by the sideloader:

```
packet_payload_size = negotiated_att_mtu - 3      # 177 bytes at MTU 180
for each packet: write_without_response(raw_file_bytes[offset : offset+packet_payload_size])
send in groups of `batch_size` (from D1 05, default 10), pacing between groups to match
observed ~150-250ms per batch rather than flooding all writes back-to-back
no additional per-packet header, sequence number, or offset field is prepended — CONFIRMED
absence in the sense that total-bytes-in equals total-bytes-out with no unaccounted overhead
byte count in the arithmetic above (if there were a header, the numbers above would not match
exactly).
```

### 5.4 Full sequence (session order) — CONFIRMED

```
1. TX D1 08  SET_FILE_INFO(original_size, compression_type=2, "name.iwf.lz")   → RX ack
2. TX D1 01  START_TRANSFER(compressed_size, compression_type=2, "name.iwf.lz") → RX ack
3. TX D1 05  SET_BATCH_SIZE(10)                                                 → RX ack
4. [raw compressed file bytes streamed — see §5.3]                              (periodic
                                                                                  local progress
                                                                                  callbacks only)
5. TX D1 03  END_TRANSFER(checksum)                                             → RX ack (status 0)
6. TX V3 0x08 APPLY_WATCHFACE("name.iwf")  (no .lz suffix)                      → RX ack
```
Step 6 is what actually makes the watch switch to the new face; steps 1-5 only place the file in
storage.

---

## 6. Compression

- The app compresses the `.iwf` file with **FastLZ** (`fastlz_util.c`,
  `"compressed 222 KB into 85 KB, compression ratio is 62%"`) before sending — CONFIRMED file is
  compressed, CONFIRMED library name; **LIKELY** compression level (FastLZ has levels 1/2; not
  stated in the log).
- `compression_type = 2` in the wire protocol is **LIKELY** the code for "FastLZ"; `0` would
  presumably mean "uncompressed" but that path is **UNKNOWN** (never exercised in this capture).
- Arnold has a separate, already-in-progress FastLZ C→Python port
  ([[fastlz-python-port]]); rather than duplicate/guess at a byte-perfect FastLZ implementation
  here, the sideloader's compression step is a pluggable interface (see code) defaulting to
  **no compression** (`compression_type=0`) until that port is ready to be wired in — sending
  uncompressed data is not confirmed to be accepted by real firmware, so this defaults to a
  conservative, clearly-logged fallback rather than a guessed reimplementation.

---

## 7. Known gaps — what would close them

1. **GATT service/characteristic UUIDs** — need a live `bleak` service discovery dump against a
   real watch (the sideloader does this automatically and logs candidates).
2. **Raw per-chunk framing during file transfer** — need a debug/verbose capture (Android
   `btsnoop_hci.log`, or a BLE sniffer) that shows the actual over-the-air writes during the
   `D1 05` → `D1 03` window; this log's `clib.D` tap did not print them.
3. **`D1 03` checksum algorithm** — need the actual bytes of a compressed `.iwf.lz` payload to
   test candidate checksums (CRC32, Adler32, etc.) against the observed value.
4. **Non-success status codes** for any `D1`-family ack (only status `0x00` was ever observed).
5. **`0xFF` sentinel byte** in `D1 08` / `D1 01` payloads — only one value ever observed.
