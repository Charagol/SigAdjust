"""MainWindow — Main application window for SigAdjust V2.

Contains a QTabWidget with 4 tabs:
  1. Data Import (DataPage)
  2. Model Setup (SetupPage)
  3. Computation Progress (placeholder for Phase 12)
  4. Results Display (placeholder for Phase 12)
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QLabel, QWidget,
    QVBoxLayout, QStatusBar,
)
from ui.widgets.page_data import DataPage
from ui.widgets.page_setup import SetupPage
from ui.widgets.page_progress import ComputationProgressPage
from ui.widgets.page_results import ResultsPage


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
        self.setStyleSheet(self._global_stylesheet())
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

    def _setup_tabs(self):
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabPosition(QTabWidget.North)


        # Tab 1: Data import
        self._data_page = DataPage(self._vm)
        self._tab_widget.addTab(self._data_page, "数据导入")

        # Tab 2: Model setup
        self._setup_page = SetupPage(self._vm, self)
        self._tab_widget.addTab(self._setup_page, "模型设定")

        # Tab 3: Computation progress
        self._progress_page = ComputationProgressPage(self._vm, self)
        self._tab_widget.addTab(self._progress_page, "计算进度")

        # Tab 4: Results display
        self._results_page = ResultsPage(self._vm)
        self._tab_widget.addTab(self._results_page, "结果展示")

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
    def _global_stylesheet() -> str:
        """Return the global QSS stylesheet for the entire application."""
        return """
            QMainWindow, QWidget {
                font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
                font-size: 13px;
                color: #374151;
            }
            QTabWidget::pane {
                border: 1px solid #e5e7eb;
                border-top: none;
                background: white;
            }
            QTabBar::tab {
                padding: 8px 20px;
                font-size: 13px;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background: white;
                border: 1px solid #e5e7eb;
                border-bottom-color: white;
                color: #4f46e5;
                font-weight: bold;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:!selected {
                background: #f9fafb;
                color: #6b7280;
                border: 1px solid transparent;
            }
            QTabBar::tab:hover:!selected {
                background: #f3f4f6;
            }
            QPushButton {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
                color: #374151;
            }
            QPushButton:hover {
                background: #f9fafb;
                border-color: #9ca3af;
            }
            QPushButton:pressed {
                background: #f3f4f6;
            }
            QPushButton:disabled {
                background: #f3f4f6;
                color: #9ca3af;
                border-color: #e5e7eb;
            }
            QLineEdit {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #4f46e5;
            }
            QComboBox {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                background: white;
                min-height: 24px;
            }
            QComboBox:hover {
                border-color: #9ca3af;
            }
            QComboBox:focus {
                border-color: #4f46e5;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                width: 0; height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #6b7280;
                margin-right: 4px;
            }
            QCheckBox {
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border-radius: 3px;
                border: 1px solid #d1d5db;
                background: white;
            }
            QCheckBox::indicator:checked {
                background: #4f46e5;
                border-color: #4f46e5;
            }
            QCheckBox::indicator:hover {
                border-color: #9ca3af;
            }
            QGroupBox {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 16px;
                font-weight: bold;
                color: #374151;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QTableWidget {
                border: 1px solid #e5e7eb;
                font-size: 12px;
                background: white;
                gridline-color: #f3f4f6;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 4px 6px;
            }
            QTableWidget::item:selected {
                background: #e0e7ff;
                color: #3730a3;
            }
            QHeaderView::section {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                padding: 4px 6px;
                font-weight: bold;
                font-size: 12px;
                color: #374151;
            }
            QScrollBar:vertical {
                background: #f3f4f6;
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #d1d5db;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9ca3af;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar:horizontal {
                background: #f3f4f6;
                height: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #d1d5db;
                border-radius: 4px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #9ca3af;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
            }
            QProgressBar {
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                text-align: center;
                font-size: 12px;
                background: #f3f4f6;
                color: #374151;
            }
            QProgressBar::chunk {
                background: #4f46e5;
                border-radius: 3px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #e5e7eb;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #4f46e5;
                width: 16px; height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #4338ca;
            }
            QToolTip {
                background: #1f2937;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QDoubleSpinBox {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 13px;
                background: white;
            }
            QDoubleSpinBox:focus {
                border-color: #4f46e5;
            }
        """

    def switch_to_tab(self, index: int):
        """Switch to the tab at the given index (0-based)."""
        if 0 <= index < self._tab_widget.count():
            self._tab_widget.setCurrentIndex(index)

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
