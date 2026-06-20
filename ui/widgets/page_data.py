"""DataPage — Data import tab for SigAdjust V2.

Allows the user to open CSV/DTA/Excel files, preview the data,
and inspect column-level metadata (dtype, missing values).
"""

import os
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QFileDialog, QGroupBox,
    QHeaderView, QFrame, QSizePolicy,
)


class DataPage(QWidget):
    """Tab 1: Data import and preview.

    Provides file selection, data preview table, and column info panel.
    Delegates data loading to the ViewModel.
    """

    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self._filepath: str | None = None
        self._setup_ui()
        self._connect_signals()

    # ── UI Setup ─────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── File selection area ──
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)

        btn_layout = QHBoxLayout()
        self._open_btn = QPushButton("Open File")
        self._open_btn.setFixedHeight(32)
        self._open_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        btn_layout.addWidget(self._open_btn)

        self._format_label = QLabel("Supported: .csv / .dta / .xlsx")
        self._format_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        btn_layout.addWidget(self._format_label)
        btn_layout.addStretch()

        file_layout.addLayout(btn_layout)

        self._filepath_label = QLabel("")
        self._filepath_label.setStyleSheet("color: #374151; font-size: 12px; padding: 2px 0;")
        self._filepath_label.setWordWrap(True)
        file_layout.addWidget(self._filepath_label)

        # Stats cards
        stats_layout = QHBoxLayout()
        self._stats_cards = {}
        for label_text in ("Rows", "Columns", "File"):
            card = QFrame()
            card.setFixedHeight(60)
            card.setMinimumWidth(120)
            card.setStyleSheet("""
                QFrame {
                    background-color: #f9fafb;
                    border: 1px solid #e5e7eb;
                    border-radius: 6px;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 4, 8, 4)

            title = QLabel(label_text)
            title.setStyleSheet("color: #9ca3af; font-size: 11px;")
            card_layout.addWidget(title)

            value = QLabel("--")
            value.setStyleSheet("color: #111827; font-size: 16px; font-weight: bold;")
            card_layout.addWidget(value)

            self._stats_cards[label_text.lower()] = value
            stats_layout.addWidget(card)

        file_layout.addLayout(stats_layout)
        layout.addWidget(file_group)

        # ── Data preview table ──
        preview_group = QGroupBox("Data Preview (first 100 rows)")
        preview_layout = QVBoxLayout(preview_group)

        self._preview_table = QTableWidget()
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e5e7eb;
                gridline-color: #f3f4f6;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                padding: 4px 6px;
                font-weight: bold;
            }
        """)
        self._preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._preview_table.setSelectionMode(QTableWidget.NoSelection)
        self._preview_table.horizontalHeader().setStretchLastSection(True)
        self._preview_table.verticalHeader().setDefaultSectionSize(22)
        preview_layout.addWidget(self._preview_table)
        layout.addWidget(preview_group, stretch=2)

        # ── Column info panel ──
        info_group = QGroupBox("Column Information")
        info_layout = QVBoxLayout(info_group)

        self._info_table = QTableWidget()
        self._info_table.setColumnCount(4)
        self._info_table.setHorizontalHeaderLabels(["Column", "Type", "Missing", "Missing Rate"])
        self._info_table.setAlternatingRowColors(True)
        self._info_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e5e7eb;
                gridline-color: #f3f4f6;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                padding: 4px 6px;
                font-weight: bold;
            }
        """)
        self._info_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._info_table.setSelectionMode(QTableWidget.NoSelection)
        self._info_table.horizontalHeader().setStretchLastSection(True)
        self._info_table.verticalHeader().setDefaultSectionSize(22)
        info_layout.addWidget(self._info_table)
        layout.addWidget(info_group, stretch=1)

    def _connect_signals(self):
        self._open_btn.clicked.connect(self._on_open_file)

    # ── Slots ────────────────────────────────────────────────────────

    def _on_open_file(self):
        """Open file dialog and load selected file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Data File",
            "",
            "Data Files (*.csv *.dta *.xlsx *.xls);;CSV Files (*.csv);;"
            "Stata Files (*.dta);;Excel Files (*.xlsx *.xls);;All Files (*)",
        )
        if not filepath:
            return

        self._filepath = filepath
        self._filepath_label.setText(f"Path: {filepath}")

        success = self._vm.load_data(filepath)
        if success:
            self._populate_preview(self._vm.df)
            self._populate_column_info(self._vm.columns_info)
            self._update_stats(filepath, self._vm.df)
        else:
            self._filepath_label.setText(f"Failed to load: {filepath}")
            self._preview_table.setRowCount(0)
            self._preview_table.setColumnCount(0)
            self._info_table.setRowCount(0)

    def _populate_preview(self, df: pd.DataFrame):
        """Fill the preview table with first 100 rows."""
        display_df = df.head(100)
        cols = display_df.columns.tolist()
        self._preview_table.setColumnCount(len(cols))
        self._preview_table.setHorizontalHeaderLabels(cols)
        self._preview_table.setRowCount(len(display_df))

        for row_idx, (_, row) in enumerate(display_df.iterrows()):
            for col_idx, col in enumerate(cols):
                val = row[col]
                text = str(val) if val is not None else ""
                item = QTableWidgetItem(text)
                self._preview_table.setItem(row_idx, col_idx, item)

        # Auto-resize columns
        self._preview_table.resizeColumnsToContents()
        self._preview_table.horizontalHeader().setStretchLastSection(True)

    def _populate_column_info(self, columns_info: dict):
        """Fill the column info table from get_missing_summary output."""
        cols_data = columns_info.get("columns", {})
        self._info_table.setRowCount(len(cols_data))

        for row_idx, (col_name, info) in enumerate(cols_data.items()):
            self._info_table.setItem(row_idx, 0, QTableWidgetItem(col_name))
            self._info_table.setItem(row_idx, 1, QTableWidgetItem(info.get("dtype", "")))
            self._info_table.setItem(row_idx, 2, QTableWidgetItem(str(info.get("n_missing", 0))))
            rate = info.get("missing_rate", 0.0)
            self._info_table.setItem(row_idx, 3, QTableWidgetItem(f"{rate:.2%}"))

        self._info_table.resizeColumnsToContents()
        self._info_table.horizontalHeader().setStretchLastSection(True)

    def _update_stats(self, filepath: str, df: pd.DataFrame):
        """Update the stats summary cards."""
        self._stats_cards["rows"].setText(f"{len(df):,}")
        self._stats_cards["columns"].setText(f"{len(df.columns):,}")

        ext = os.path.splitext(filepath)[1].upper().lstrip(".")
        self._stats_cards["file"].setText(ext)
