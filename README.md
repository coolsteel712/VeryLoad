VERYLOAD - VeryFit Watch Face Sideloader
=========================================

A cross-platform desktop application for sideloading custom watch faces onto
VeryFit/IDO smartwatches via BLE.

FEATURES
--------

- BLE Device Discovery - Scan for nearby compatible smartwatches
- Watch Face Upload - Upload .iwf watch face files to your device
- Real-time Progress - Visual progress bar with status logging
- Automatic Compression - FastLZ compression for efficient transfers (optional)
- Cancellation Support - Cancel ongoing uploads at any time
- Cross-platform - Works on Windows, macOS, and Linux

PREREQUISITES
-------------

- Python 3.10 or higher
- A VeryFit/IDO compatible smartwatch
- Bluetooth LE adapter

INSTALLATION
------------

1. Clone the repository

   git clone https://github.com/coolsteel712/veryload
   cd veryload

2. Set up a virtual environment (recommended)

   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies

   pip install -r requirements.txt

4. Run the application

   python main.py

USAGE GUIDE
-----------

1. Connect to your watch

   a. Click Scan to discover nearby BLE devices
   b. Select your watch from the list
   c. Click Connect to establish a connection

2. Select a watch face

   a. Click Browse... to open a file dialog
   b. Navigate to and select your .iwf watch face file
   c. The filename will appear next to the browse button

3. Upload the watch face

   a. Click Upload to start the transfer
   b. Monitor the progress bar and status log
   c. Wait for the "Upload complete" confirmation
   d. The watch face should now be installed on your device

4. Cancel an upload

   - Click Cancel during an active upload to stop the transfer

PROTOCOL DETAILS
----------------

VeryLoad implements the complete VeryFit BLE protocol for watch face uploads:

- Scanning - BLE device discovery with configurable timeout
- Connection - Secure BLE connection establishment
- Transfer Control - D1 protocol frames for file metadata and transfer management
- Data Streaming - Chunked file transfer with progress tracking
- Verification - End-to-end checksum validation
- Application - V3 command frames to apply the watch face

TECHNICAL NOTES
---------------

Compression

The application supports two compression modes:
- FastLZ (default) - Real FastLZ level-1 compression, matching the official app
- None - Direct file upload without compression (useful for debugging)

Protocol Implementation

All protocol fields have been validated against captured traffic from the
official VeryFit app. See PROTOCOL_SPEC.md for detailed documentation.

Known Limitations

- Only .iwf watch face files are supported
- Requires a compatible VeryFit/IDO device
- Upload may be interrupted by poor BLE signal strength

TROUBLESHOOTING
---------------

"No BLE devices found"
- Ensure your watch is in discoverable mode
- Check that Bluetooth is enabled on your computer
- Try moving closer to the watch

"Connection failed"
- Restart your watch and try again
- Ensure no other app is connected to the watch
- Check your BLE adapter drivers

"Upload failed"
- Verify the .iwf file is valid
- Check that you have sufficient storage on the watch
- Try using the uncompressed mode

DEVELOPMENT
-----------

Running tests

   pytest tests/

Building executable

   pyinstaller veryload.spec

CONTRIBUTING
------------

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

LICENSE
-------

This project is licensed under the GNU General Public License v3.0.

DISCLAIMER
----------

- This software is not affiliated with VeryFit or IDO.
- **SIDELOADING WATCH FACES ON YOUR VERYFIT WATCH WILL CAUSE THE WARRANTY TO VOID AND CANNOT BE REPAIRED IF BOOTLOOPS HAPPEN. USE THIS TOOL AT YOUR OWN RISK.**

ACKNOWLEDGMENTS
---------------

- Based on reverse engineering work from the VeryFit protocol
- FastLZ reference implementation by Ariya Hidayat
- Built with Bleak and PyQt6

SUPPORT
-------

For issues and questions, please open an issue on GitHub:
https://github.com/coolsteel712/veryload/issues
