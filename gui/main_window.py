"""
PyQt6 main window for the VeryLoad app.

Layout follows the requested mockup:

    Device: [Scan] -> Nearby Devices list -> [Connect] -> Selected Watch
    IWF File: [Browse...]
    Upload Progress: progress bar
    Status Log: scrolling log
    [Upload] [Cancel]

BLE work runs on the Qt event loop via ``qasync`` so bleak's asyncio calls
never block the UI thread.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from errors import SideloaderError
from uploader import WatchFaceUploader

logger = logging.getLogger("veryfit_sideloader.gui")


class QtLogHandler(logging.Handler):
    """Forwards Python logging records into the on-screen status log."""

    def __init__(self, append_fn):
        super().__init__()
        self._append_fn = append_fn

    def emit(self, record: logging.LogRecord) -> None:
        self._append_fn(self.format(record))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VeryLoad - Watch Face Sideloader")
        self.resize(560, 640)

        self.uploader = WatchFaceUploader()
        self._devices = []
        self._selected_device = None
        self._selected_file: Optional[Path] = None
        self._connected = False
        self._cancel_event: Optional[asyncio.Event] = None

        self._build_ui()
        self._wire_logging()

    # -- UI construction ------------------------------------------------------
    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        # Device group
        device_group = QGroupBox("Device")
        device_layout = QVBoxLayout(device_group)

        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self._on_scan_clicked)
        device_layout.addWidget(self.scan_button)

        device_layout.addWidget(QLabel("Nearby Devices"))
        self.device_list = QListWidget()
        device_layout.addWidget(self.device_list)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._on_connect_clicked)
        device_layout.addWidget(self.connect_button)

        self.selected_watch_label = QLabel("Selected Watch: (none)")
        device_layout.addWidget(self.selected_watch_label)

        layout.addWidget(device_group)

        # File group
        file_group = QGroupBox("IWF File")
        file_layout = QHBoxLayout(file_group)
        self.file_label = QLabel("(no file selected)")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._on_browse_clicked)
        file_layout.addWidget(self.file_label, stretch=1)
        file_layout.addWidget(self.browse_button)
        layout.addWidget(file_group)

        # Progress
        progress_group = QGroupBox("Upload Progress")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        layout.addWidget(progress_group)

        # Status log
        log_group = QGroupBox("Status Log")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        layout.addWidget(log_group, stretch=1)

        # Action buttons
        actions_layout = QHBoxLayout()
        self.upload_button = QPushButton("Upload")
        self.upload_button.clicked.connect(self._on_upload_clicked)
        self.upload_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.cancel_button.setEnabled(False)
        actions_layout.addWidget(self.upload_button)
        actions_layout.addWidget(self.cancel_button)
        layout.addLayout(actions_layout)

        self.setCentralWidget(root)

    def _wire_logging(self) -> None:
        handler = QtLogHandler(self._append_log)
        handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))
        logging.getLogger("veryfit_sideloader").addHandler(handler)
        logging.getLogger("veryfit_sideloader").setLevel(logging.INFO)

    def _append_log(self, line: str) -> None:
        self.log_view.append(line)

    # -- event handlers (each schedules an asyncio task via qasync) ------------
    def _on_scan_clicked(self) -> None:
        asyncio.ensure_future(self._scan())

    def _on_connect_clicked(self) -> None:
        asyncio.ensure_future(self._connect())

    def _on_browse_clicked(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, "Select .iwf file", "", "Watch face (*.iwf)")
        if path_str:
            self._selected_file = Path(path_str)
            self.file_label.setText(self._selected_file.name)
            self._update_upload_enabled()

    def _on_upload_clicked(self) -> None:
        asyncio.ensure_future(self._upload())

    def _on_cancel_clicked(self) -> None:
        if self._cancel_event:
            self._cancel_event.set()
            self._append_log("Cancel requested...")

    def _update_upload_enabled(self) -> None:
        self.upload_button.setEnabled(self._connected and self._selected_file is not None)

    # -- async workflows --------------------------------------------------------
    async def _scan(self) -> None:
        self.scan_button.setEnabled(False)
        self.device_list.clear()
        self._append_log("Scanning...")
        try:
            devices = await self.uploader.scan(timeout=6.0)
            self._devices = devices
            for d in devices:
                label = f"{d.name or 'Unknown'}  [{d.address}]"
                item = QListWidgetItem(label)
                self.device_list.addItem(item)
            self._append_log(f"Found {len(devices)} device(s)")
        except SideloaderError as exc:
            self._append_log(f"Scan error: {exc}")
        finally:
            self.scan_button.setEnabled(True)

    async def _connect(self) -> None:
        row = self.device_list.currentRow()
        if row < 0 or row >= len(self._devices):
            QMessageBox.warning(self, "No device selected", "Select a device from the list first.")
            return
        device = self._devices[row]
        self.connect_button.setEnabled(False)
        self._append_log(f"Connecting to {device.name or device.address}...")
        try:
            await self.uploader.connect(device)
            self._connected = True
            self._selected_device = device
            self.selected_watch_label.setText(f"Selected Watch: {device.name or device.address}")
            self._append_log("Connected.")
        except SideloaderError as exc:
            self._append_log(f"Connection failed: {exc}")
            QMessageBox.critical(self, "Connection failed", str(exc))
        finally:
            self.connect_button.setEnabled(True)
            self._update_upload_enabled()

    async def _upload(self) -> None:
        if not self._selected_file:
            return
        self.upload_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self._cancel_event = asyncio.Event()

        def on_progress(sent: int, total: int) -> None:
            pct = int(sent * 100 / total) if total else 0
            self.progress_bar.setValue(pct)

        try:
            result = await self.uploader.upload(
                self._selected_file,
                on_progress=on_progress,
                on_log=self._append_log,
                cancel_event=self._cancel_event,
            )
            self.progress_bar.setValue(100)
            self._append_log(
                f"Upload complete: {result.filename_on_watch} "
                f"({result.sent_size}/{result.original_size} bytes, "
                f"compression_type={result.compression_type})"
            )
            QMessageBox.information(self, "Upload complete", "Watch face installed successfully.")
        except asyncio.CancelledError:
            self._append_log("Upload cancelled.")
        except SideloaderError as exc:
            self._append_log(f"Upload failed: {exc}")
            QMessageBox.critical(self, "Upload failed", str(exc))
        finally:
            self.cancel_button.setEnabled(False)
            self._cancel_event = None
            self._update_upload_enabled()

    async def _disconnect(self) -> None:
        if self._connected:
            await self.uploader.disconnect()
            self._connected = False
            self._update_upload_enabled()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        asyncio.ensure_future(self._disconnect())
        super().closeEvent(event)
