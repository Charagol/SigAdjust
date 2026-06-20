"""VariableSelector — tag-based multi-select dropdown widget.

A reusable component for selecting variables from a list.
Selected items appear as tags (chips) with × removal buttons.
The dropdown shows candidate items as clickable pill buttons.
Supports search filtering, preselect, and conflict-aware selection.

Visual structure:
  +---------------------------------------+
  | [tag1 ×] [tag2 ×] [tag3 ×]           |
  | search input...                       |
  +---------------------------------------+
  | +-------+ +-------+                  |
  | | var_x | | var_y |  <- candidate    |
  | +-------+ +-------+     pills        |
  | +-------+                            |
  | | var_z |                            |
  | +-------+                            |
  +---------------------------------------+
"""

from PySide6.QtCore import Qt, Signal, QRect, QSize, QPoint
from PySide6.QtGui import QFontMetrics, QIcon, QAction
from PySide6.QtWidgets import (
    QWidget, QLayout, QSizePolicy, QLineEdit, QPushButton,
    QFrame, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QApplication,
)


# ── FlowLayout ────────────────────────────────────────────────────────

class FlowLayout(QLayout):
    """Layout that wraps items to the next row when horizontal space runs out.

    Adapted from the canonical Qt FlowLayout example.
    """

    def __init__(self, parent=None, margin=0, spacing=4):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._item_list = []

    def __del__(self):
        while self._item_list:
            item = self._item_list.pop()
            self.removeItem(item)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins().left() + self.contentsMargins().right()
        size += QSize(margin, margin)
        return size

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def _do_layout(self, rect, test_only):
        x = rect.x() + self.contentsMargins().left()
        y = rect.y() + self.contentsMargins().top()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            widget = item.widget()
            if widget and not widget.isVisible():
                continue
            space_x = self.contentsMargins().left() + self.contentsMargins().right()
            space_w = rect.width() - space_x
            item_size = item.sizeHint()

            if x + item_size.width() > rect.x() + space_w and line_height > 0:
                x = rect.x() + self.contentsMargins().left()
                y += line_height + spacing
                line_height = 0

            item.setGeometry(QRect(QPoint(x, y), item_size))

            x += item_size.width() + spacing
            line_height = max(line_height, item_size.height())

        return y + line_height - rect.y()


# ── TagChip ───────────────────────────────────────────────────────────

class TagChip(QFrame):
    """A single tag (chip) in the VariableSelector tag area.

    Shows label text plus an × removal button.
    """

    removed = Signal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("tagChip")
        self.setStyleSheet("""
            #tagChip {
                background-color: #e0e7ff;
                border: 1px solid #a5b4fc;
                border-radius: 4px;
                padding: 2px 4px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)

        label = QLabel(self._text)
        label.setStyleSheet("border: none; background: transparent; color: #3730a3;")
        layout.addWidget(label)

        btn = QPushButton("\u00d7")
        btn.setFixedSize(18, 18)
        btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #6366f1;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                color: #dc2626;
            }
        """)
        btn.clicked.connect(lambda: self.removed.emit(self._text))
        layout.addWidget(btn)

    @property
    def text(self) -> str:
        return self._text


# ── VariableSelector ──────────────────────────────────────────────────

class VariableSelector(QWidget):
    """Tag-based multi-select dropdown widget with search.

    Signals:
        selection_changed: Emitted when selection changes, carries list of names.
    """

    selection_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_items: list[str] = []
        self._selected: list[str] = []
        self._filtered_items: list[str] = []
        self._max_selection: int = 0  # 0 = unlimited
        self._setup_ui()

    # ── Public API ───────────────────────────────────────────────────

    def set_items(self, items: list[str]):
        """Set the full list of candidate items."""
        self._all_items = list(items)
        self._filtered_items = list(items)
        self._rebuild_candidates()

    def set_max_selection(self, n: int):
        """Set maximum number of items that can be selected (0 = unlimited)."""
        self._max_selection = n

    def set_selected(self, selected: list[str]):
        """Set which items are currently selected."""
        self._selected = list(selected)
        self._rebuild_tags()
        self._rebuild_candidates()
        self.selection_changed.emit(list(self._selected))

    def get_selected(self) -> list[str]:
        """Get the list of currently selected item names."""
        return list(self._selected)

    # ── UI Setup ─────────────────────────────────────────────────────

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # Search input
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\U0001f50d Search variables...")
        self._search_box.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 13px;
            }
        """)
        self._search_box.textChanged.connect(self._on_search_changed)
        self._search_box.installEventFilter(self)
        search_layout.addWidget(self._search_box)
        main_layout.addLayout(search_layout)

        # Tag area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMaximumHeight(80)
        scroll.setStyleSheet("border: none; background: transparent;")

        self._tag_container = QWidget()
        self._tag_container.setStyleSheet("background: transparent;")
        self._tag_layout = FlowLayout(self._tag_container, margin=0, spacing=4)
        scroll.setWidget(self._tag_container)
        main_layout.addWidget(scroll)

        # Dropdown popup with candidates
        self._popup = QFrame(self)
        self._popup.setWindowFlags(Qt.Popup)
        self._popup.setFrameShape(QFrame.StyledPanel)
        self._popup.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
            }
        """)
        popup_layout = QVBoxLayout(self._popup)
        popup_layout.setContentsMargins(4, 4, 4, 4)
        popup_layout.setSpacing(4)

        self._candidate_scroll = QScrollArea()
        self._candidate_scroll.setWidgetResizable(True)
        self._candidate_scroll.setStyleSheet("border: none;")
        self._candidate_scroll.setMinimumHeight(60)
        self._candidate_scroll.setMaximumHeight(200)

        self._candidate_container = QWidget()
        self._candidate_container.setStyleSheet("background: transparent;")
        self._candidate_layout = FlowLayout(self._candidate_container, margin=0, spacing=4)
        self._candidate_scroll.setWidget(self._candidate_container)
        popup_layout.addWidget(self._candidate_scroll)

    def _rebuild_tags(self):
        """Rebuild the tag chip display area."""
        # Remove existing items
        while self._tag_layout.count():
            item = self._tag_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        for name in self._selected:
            chip = TagChip(name)
            chip.removed.connect(self._on_tag_removed)
            self._tag_layout.addWidget(chip)

    def _rebuild_candidates(self):
        """Rebuild the candidate pill buttons in the dropdown."""
        # Remove existing items
        while self._candidate_layout.count():
            item = self._candidate_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        selected_set = set(self._selected)
        self._filtered_items = [
            item for item in self._all_items
            if item not in selected_set
        ]

        # Apply search filter
        query = self._search_box.text().strip().lower()
        if query:
            self._filtered_items = [
                item for item in self._filtered_items
                if query in item.lower()
            ]

        for name in self._filtered_items:
            btn = QPushButton(name)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f3f4f6;
                    border: 1px solid #d1d5db;
                    border-radius: 4px;
                    padding: 2px 10px;
                    font-size: 12px;
                    color: #374151;
                }
                QPushButton:hover {
                    background-color: #e0e7ff;
                    border-color: #a5b4fc;
                    color: #3730a3;
                }
            """)
            btn.clicked.connect(lambda checked, n=name: self._select_item(n))
            self._candidate_layout.addWidget(btn)

    def _select_item(self, name: str):
        """Add an item to the selected list. Respects max_selection limit."""
        if name not in self._selected:
            if self._max_selection > 0 and len(self._selected) >= self._max_selection:
                self._selected.pop(0)  # FIFO replacement
            self._selected.append(name)
            self._rebuild_tags()
            self._rebuild_candidates()
            self.selection_changed.emit(list(self._selected))
            self._search_box.clear()

    def _on_tag_removed(self, name: str):
        """Remove an item from the selected list."""
        if name in self._selected:
            self._selected.remove(name)
            self._rebuild_tags()
            self._rebuild_candidates()
            self.selection_changed.emit(list(self._selected))

    def _on_search_changed(self, text: str):
        """Handle search input changes."""
        self._rebuild_candidates()
        if not self._popup.isVisible() and text.strip():
            self._show_popup()
        elif self._popup.isVisible() and not text.strip() and not self._filtered_items:
            self._popup.hide()

    def _show_popup(self):
        """Show the candidate dropdown popup."""
        pos = self.mapToGlobal(QPoint(0, self.height()))
        self._popup.move(pos)
        self._popup.setMinimumWidth(self.width())
        self._popup.adjustSize()
        self._popup.show()

    def _hide_popup(self):
        """Hide the candidate dropdown popup."""
        self._popup.hide()

    # ── Event Handling ───────────────────────────────────────────────

    def eventFilter(self, obj, event):
        """Handle search box events: click to toggle, Escape to close."""
        if obj is self._search_box:
            if event.type() == event.Type.MouseButtonPress:
                # Toggle popup without interfering with text cursor
                if self._popup.isVisible():
                    self._hide_popup()
                elif self._all_items:
                    self._filtered_items = [
                        item for item in self._all_items
                        if item not in set(self._selected)
                    ]
                    self._rebuild_candidates()
                    self._show_popup()
                return False  # let search box handle normal click behavior
            elif event.type() == event.Type.KeyPress:
                if event.key() == Qt.Key_Escape:
                    self._hide_popup()
                    return True
            # FocusIn / FocusOut deliberately ignored to avoid recursion
        return super().eventFilter(obj, event)
    def mousePressEvent(self, event):
        """Hide popup when clicking outside."""
        if self._popup.isVisible():
            rect = self.rect().united(
                QRect(self._popup.pos() - self.mapToGlobal(QPoint(0, 0)),
                      self._popup.size())
            )
            if not rect.contains(event.pos()):
                self._hide_popup()
        super().mousePressEvent(event)
