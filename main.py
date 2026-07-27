"""
Entry point. Uses ``qasync`` to run bleak's asyncio calls on the same loop as
the Qt event loop, so the GUI never blocks during scan/connect/upload.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from PyQt6.QtWidgets import QApplication
import qasync

from gui.main_window import MainWindow


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")

    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        return loop.run_forever()


if __name__ == "__main__":
    sys.exit(main())
