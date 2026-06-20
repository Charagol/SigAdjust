"""Tests for SetupPage — model configuration page.

Uses qtbot (pytest-qt) for QApplication lifecycle management.
"""

import json
import os
import tempfile

import pytest
from PySide6.QtWidgets import QWidget

from ui.viewmodel import SigAdjustViewModel
from ui.widgets.page_setup import SetupPage


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures")


class MockMainWindow(QWidget):
    """Minimal mock MainWindow for testing SetupPage."""

    def __init__(self):
        super().__init__()
        self._current_tab = 0

    def switch_to_tab(self, index: int):
        self._current_tab = index


def _create_page(qtbot, load_data=True):
    """Helper: create a fresh SetupPage with loaded data."""
    vm = SigAdjustViewModel()
    if load_data:
        csv_path = os.path.join(DATA_DIR, "sample.csv")
        vm.load_data(csv_path)
    mock = MockMainWindow()
    page = SetupPage(vm, mock)
    return vm, mock, page


# ── Tests ────────────────────────────────────────────────────────────

class TestSetupPageGlobalSettings:
    """Verify global settings default values."""

    def test_default_threshold(self, qtbot):
        _, _, page = _create_page(qtbot)
        assert page._threshold_spin.value() == 0.05

    def test_default_max_pct(self, qtbot):
        _, _, page = _create_page(qtbot)
        assert page._max_pct_spin.value() == 5.0

    def test_default_direction(self, qtbot):
        _, _, page = _create_page(qtbot)
        assert page._direction_combo.currentText() == "both"


class TestSetupPageModelCards:
    """Verify add/remove model card behavior."""

    def test_initial_card_count(self, qtbot):
        _, _, page = _create_page(qtbot)
        assert len(page._model_cards) == 1

    def test_add_card_increases_count(self, qtbot):
        _, _, page = _create_page(qtbot)
        page._add_model_card()
        assert len(page._model_cards) == 2

    def test_add_card_up_to_four(self, qtbot):
        _, _, page = _create_page(qtbot)
        page._add_model_card()
        page._add_model_card()
        page._add_model_card()
        assert len(page._model_cards) == 4
        page._add_model_card()
        assert len(page._model_cards) == 4

    def test_remove_card_decreases_count(self, qtbot):
        _, _, page = _create_page(qtbot)
        page._add_model_card()
        page._add_model_card()
        page._add_model_card()
        page._on_remove_model(3)
        assert len(page._model_cards) == 3
        page._on_remove_model(2)
        assert len(page._model_cards) == 2

    def test_cannot_remove_last_card(self, qtbot):
        _, _, page = _create_page(qtbot)
        assert len(page._model_cards) == 1
        page._on_remove_model(0)
        assert len(page._model_cards) == 1


class TestSetupPageVariableConflict:
    """Verify XY mutual exclusion and Control filtering."""

    def test_control_excludes_x(self, qtbot):
        _, _, page = _create_page(qtbot)
        card = page._model_cards[0]
        card.x_selector.set_selected(["y"])
        page._on_x_changed(0, ["y"])
        control_items = card.control_selector._all_items
        assert "y" not in control_items

    def test_control_excludes_y(self, qtbot):
        _, _, page = _create_page(qtbot)
        card = page._model_cards[0]
        card.y_selector.set_selected(["x"])
        page._on_y_changed(0, ["x"])
        control_items = card.control_selector._all_items
        assert "x" not in control_items


class TestSetupPageConfigPersistence:
    """Verify config building and JSON save/load roundtrip."""

    def test_build_config_structure(self, qtbot):
        _, _, page = _create_page(qtbot)
        config = page._build_config()
        assert "version" in config
        assert "global_settings" in config
        assert "models" in config
        assert len(config["models"]) >= 1

    def test_config_json_roundtrip(self, qtbot):
        _, _, page = _create_page(qtbot)
        card = page._model_cards[0]
        card._name_input.setText("TestModel")
        card.y_selector.set_selected(["y"])
        card.x_selector.set_selected(["x"])
        card.control_selector.set_selected(["c1"])
        page._on_y_changed(0, ["y"])

        config = page._build_config()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            tmp_path = f.name

        try:
            with open(tmp_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["version"] == config["version"]
            assert (
                loaded["global_settings"]["significance_threshold"]
                == config["global_settings"]["significance_threshold"]
            )
            assert loaded["models"][0]["name"] == "TestModel"
            assert loaded["models"][0]["dependent_var"] == "y"
            assert loaded["models"][0]["key_var"] == "x"
            assert "c1" in loaded["models"][0]["control_vars"]
        finally:
            os.unlink(tmp_path)


class TestSetupPageValidation:
    """Verify validation logic catches empty configurations."""

    def test_validation_blocks_empty_fields(self, qtbot):
        vm, mock, page = _create_page(qtbot, load_data=True)
        card = page._model_cards[0]
        card.y_selector.set_selected([])
        card.x_selector.set_selected([])

        page._on_start_analysis()

        assert vm.config is None
        assert mock._current_tab == 0
