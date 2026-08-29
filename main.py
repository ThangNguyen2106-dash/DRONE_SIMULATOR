import os
import sys

# A --windowed/--noconsole PyInstaller build has no attached
# console, so sys.stdout/stderr are None (not just redirected
# — literally None). Every print() and any code touching
# sys.stdout directly (e.g. mav_logger's isatty() check) would
# crash the instant it runs. Must happen before any other
# import, since some of those print/log at import time.

if sys.stdout is None:

    sys.stdout = open(os.devnull, "w")

if sys.stderr is None:

    sys.stderr = open(os.devnull, "w")

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():

    app = QApplication(
        sys.argv
    )

    window = MainWindow()

    window.showMaximized()

    return app.exec()


if __name__ == "__main__":
    sys.exit(
        main()
    )