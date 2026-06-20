"""SigAdjust — Application entry point (V2 PySide6).

Initializes the QApplication, creates the ViewModel singleton,
builds the MainWindow, and enters the Qt event loop.
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from ui.viewmodel import SigAdjustViewModel
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SigAdjust")
    app.setOrganizationName("SigAdjust")
    app.setStyle("Fusion")

    # Optional: set a global font
    from PySide6.QtGui import QFont
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Create singleton ViewModel
    viewmodel = SigAdjustViewModel()

    # Build and show the main window
    window = MainWindow(viewmodel)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
