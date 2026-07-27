# VeryLoad - VeryFit Watch Face Sideloader

A cross-platform desktop application for sideloading custom watch faces onto **VeryFit/IDO smartwatches** using Bluetooth Low Energy (BLE).

VeryLoad provides a complete workflow for discovering compatible devices, transferring `.iwf` watch face files, and applying custom watch faces without requiring the official VeryFit application.

> ⚠️ **Warning:** This tool uses a reverse-engineered protocol. Sideloading custom watch faces may void your device warranty. Incorrect files or interrupted transfers may cause watch face corruption or, in rare cases, boot issues. Use at your own risk.

> ❌ **IMPORTANT**: Do not use the IWFmake .iwf compiler. It generates watch face files that shows no output on VeryFit devices, including on VeryEmulate (VortexWatch Studio's Watch Face Emulator) and can cause your watch to enter a boot loop or, in rare cases, become permanently unusable ("hard-bricked"). Use the official IDO watch face compiler, ActionsDialMake, instead.
---

## Features

- **BLE Device Discovery**  
  Scan and identify nearby compatible VeryFit/IDO smartwatches.

- **Watch Face Uploading**  
  Upload custom `.iwf` watch face files directly to your device.

- **Real-Time Transfer Progress**  
  Monitor upload status with progress tracking and detailed logs.

- **FastLZ Compression Support**  
  Optional FastLZ compression matching the official VeryFit transfer method.

- **Upload Cancellation**  
  Safely cancel an active transfer at any time.

- **Cross-Platform Support**  
  Runs on Windows, macOS, and Linux.

- **Reverse-Engineered Protocol Implementation**  
  Implements the required BLE communication layers for watch face transfers.

---

# Requirements

## Software

- Python **3.10 or newer**
- BLE-compatible operating system
- Bluetooth LE adapter

## Hardware

- A VeryFit/IDO compatible smartwatch
- Bluetooth enabled on your computer

---

# Installation

## 1. Clone the repository

```bash
git clone https://github.com/coolsteel712/veryload
cd veryload
```

## 2. Create a virtual environment (recommended)

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Launch VeryLoad

```bash
python main.py
```

---

# Usage Guide

## 1. Connect Your Watch

1. Open VeryLoad.
2. Click **Scan** to search for nearby BLE devices.
3. Select your VeryFit/IDO smartwatch.
4. Click **Connect**.

---

## 2. Select a Watch Face

1. Click **Browse...**
2. Select a valid `.iwf` watch face file.
3. Confirm that the filename appears in the application.

---

## 3. Upload the Watch Face

1. Click **Upload**.
2. Monitor the progress bar and transfer log.
3. Wait until:

```
Upload complete
```

appears.

The watch should now apply the uploaded watch face.

---

## 4. Cancel an Upload

During an active transfer:

- Click **Cancel** to stop the upload process.

---

# Protocol Implementation

VeryLoad implements the VeryFit BLE watch face transfer protocol:

### Device Discovery

- BLE scanning
- Device identification
- Compatible watch detection

### Connection Layer

- BLE GATT connection handling
- Communication channel initialization

### Transfer Protocol

- D1 protocol frames for:
  - File metadata
  - Transfer initialization
  - Transfer control

- Chunked binary data streaming
- Transfer progress calculation
- Checksum verification

### Watch Face Application

- V3 protocol commands
- Watch face activation requests

---

# Technical Details

## Compression
VeryLoad supports:

### FastLZ (Default)

- Real FastLZ level-1 compression
- Compatible with the compression method used by the official VeryFit application

### Uncompressed Mode

- Sends raw `.iwf` data
- Useful for debugging and protocol testing

---

# Supported Devices

Compatibility depends on the firmware implementation of the watch.

Confirmed working:

| Device | Status |
|--------|--------|
| IDW20 | ✅ Tested |

Other VeryFit/IDO devices may work if they use the same watch face protocol.

---

# Known Limitations

- Only `.iwf` watch face files are supported.
- Requires a compatible VeryFit/IDO smartwatch.
- BLE instability may interrupt transfers.
- Some firmware versions may reject unsupported watch faces.
- Custom watch faces cannot be recovered if a malformed file causes firmware-level issues.

---

# Troubleshooting

## "No BLE devices found"

Try:

- Ensure Bluetooth is enabled.
- Make sure the watch is awake.
- Enable discoverable mode if supported.
- Move closer to the watch.
- Verify your computer has BLE support.

---

## "Connection failed"

Try:

- Restarting the watch.
- Disconnecting the watch from VeryFit or other apps.
- Restarting Bluetooth.
- Updating BLE adapter drivers.

---

## "Upload failed"

Check:

- The `.iwf` file is valid.
- The watch has enough storage.
- BLE connection quality is stable.

You can also try disabling compression.

---

# Development

## Run Tests

```bash
pytest tests/
```

## Build Executable

```bash
pyinstaller veryload.spec
```

---

# Contributing

Contributions are welcome.

1. Fork this repository.
2. Create a feature branch.
3. Make your changes.
4. Submit a pull request.

---

# License

VeryLoad is licensed under the:

**GNU General Public License v3.0**

---

# Disclaimer

VeryLoad is an independent community project.

- This project is **not affiliated with VeryFit, Shenzhen DO Intelligent Technology Co., Ltd., or IDO**.
- The watch face protocol was implemented through reverse engineering.
- Sideloading unsupported watch faces may damage your device or void warranty coverage.
- Use this software at your own risk.

---

# Acknowledgements

- Reverse engineering research of the VeryFit BLE protocol
- FastLZ reference implementation by Ariya Hidayat
- [Bleak](https://github.com/hbldh/bleak) BLE framework
- PyQt6 GUI framework

---

# Success: Watch Face Sideloading (IDW20)

VeryLoad has successfully demonstrated custom watch face sideloading on the **VeryFit IDW20**.

The device accepts modified `.iwf` watch faces transferred directly through BLE.

<img width="3000" height="4000" alt="IDW20 VeryFit watch face sideloading result" src="https://github.com/user-attachments/assets/3a7c6a86-1d4c-42fa-ad1f-6a85f9318b16" />

<img width="1080" height="2340" alt="VeryFit application showing modified watch face" src="https://github.com/user-attachments/assets/b57248a9-a3b5-4eb5-8252-66ca36fbb889" />

---

# Compiling Watch Faces
Use the ActionsDialMake compiler tool to compile a folder (iwf.json required, iwf1 or font.json is optional) into an .iwf file.

# Support

For bugs, questions, or protocol research discussions:

Open an issue:

https://github.com/coolsteel712/veryload/issues
