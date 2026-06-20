"""MainWindow — Main application window for SigAdjust V2.

Contains a QTabWidget with 4 tabs:
  1. Data Import (DataPage)
  2. Model Setup (placeholder for Phase 10)
  3. Computation Progress (placeholder for Phase 12)
  4. Results Display (placeholder for Phase 12)
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QLabel, QWidget,
    QVBoxLayout, QStatusBar,
)
from ui.widgets.page_data import DataPage


class MainWindow(QMainWindow):
    """Main application window with tab navigation."""

    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self._setup_window()
        self._setup_tabs()
        self._setup_statusbar()

    def _setup_window(self):
        self.setWindowTitle("SigAdjust \u2014 \u663e\u8457\u6027\u8c03\u6574\u5de5\u5177")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

    def _setup_tabs(self):
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabPosition(QTabWidget.North)
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e5e7eb;
                border-top: none;
            }
            QTabBar::tab {
                padding: 8px 20px;
                font-size: 13px;
                border: 1px solid transparent;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border-color: #e5e7eb;
                border-bottom-color: white;
                color: #4f46e5;
                font-weight: bold;
            }
            QTabBar::tab:!selected {
                background: #f9fafb;
                color: #6b7280;
            }
            QTabBar::tab:hover:!selected {
                background: #f3f4f6;
            }
        """)

        # Tab 1: Data import
        self._data_page = DataPage(self._vm)
        self._tab_widget.addTab(self._data_page, "Data Import")

        # Tab 2: Model setup (placeholder)
        placeholder_setup = self._make_placeholder("Model configuration will be implemented in Phase 10")
        self._tab_widget.addTab(placeholder_setup, "Model Setup")

        # Tab 3: Computation progress (placeholder)
        placeholder_progress = self._make_placeholder("Computation progress will be implemented in Phase 12")
        self._tab_widget.addTab(placeholder_progress, "Computation")

        # Tab 4: Results display (placeholder)
        placeholder_results = self._make_placeholder("Results display will be implemented in Phase 12")
        self._tab_widget.addTab(placeholder_results, "Results")

        self.setCentralWidget(self._tab_widget)

    def _setup_statusbar(self):
        status_bar = self.statusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background: #f9fafb;
                border-top: 1px solid #e5e7eb;
                font-size: 12px;
                color: #6b7280;
            }
        """)
        status_bar.showMessage("v2.0.0-dev")

    @staticmethod
    def _make_placeholder(text: str) -> QWidget:
        """Create a placeholder tab with centered text."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        label = QLabel(text)
        label.setStyleSheet("color: #9ca3af; font-size: 16px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        return widget
