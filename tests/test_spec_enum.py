"""Tests for core.spec_enum — control variable combination enumeration."""

from core.spec_enum import generate_specs


def test_generate_specs_single_var():
    specs = generate_specs(["c1"])
    assert len(specs) == 1
    assert specs[0]["control_set"] == ["c1"]
    assert specs[0]["spec_label"] == "c1"


def test_generate_specs_three_vars():
    specs = generate_specs(["c1", "c2", "c3"])
    # 2^3 - 1 = 7 non-empty subsets
    assert len(specs) == 7

    labels = {s["spec_label"] for s in specs}
    assert "c1" in labels
    assert "c1+c2+c3" in labels
    assert "c2+c3" in labels


def test_generate_specs_empty():
    specs = generate_specs([])
    assert specs == []
