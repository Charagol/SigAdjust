"""Tests for StataCommandParser — pure logic, no Qt dependency.

Tests command recognition, variable splitting, factor variable detection,
option parsing, reghdfe absorb(), and error handling.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui.widgets.stata_parser import StataCommandParser

P = StataCommandParser.parse


# ── Tests ─────────────────────────────────────────────────────────────

class TestStataParser:
    """StataCommandParser pure-logic tests."""

    def test_parse_reg_basic(self):
        """reg Y X c1 c2 -> OLS, Y, X, [c1, c2]"""
        r = P("reg Y X c1 c2")
        assert r["success"] is True
        assert r["model_type"] == "ols"
        assert r["dependent_var"] == "Y"
        assert r["key_var"] == "X"
        assert r["control_vars"] == ["c1", "c2"]

    def test_parse_logit_basic(self):
        """logit Y X c1 -> logit type"""
        r = P("logit Y X c1")
        assert r["success"] is True
        assert r["model_type"] == "logit"
        assert r["dependent_var"] == "Y"
        assert r["key_var"] == "X"
        assert r["control_vars"] == ["c1"]

    def test_parse_reghdfe(self):
        """reghdfe Y X c1, absorb(industry) -> fe, fe_vars"""
        r = P("reghdfe Y X c1, absorb(industry)")
        assert r["success"] is True
        assert r["model_type"] == "fe"
        assert r["fe_vars"] == ["industry"]

    def test_parse_robust_se(self):
        """reg Y X, robust -> se_type=robust"""
        r = P("reg Y X, robust")
        assert r["success"] is True
        assert r["se_type"] == "robust"

    def test_parse_factor_variable(self):
        """reg Y X i.industry -> factor_vars detected"""
        r = P("reg Y X i.industry")
        assert r["success"] is True
        assert r["factor_vars"] == ["industry"]
        # i.industry should NOT appear in control_vars
        assert "i.industry" not in r["control_vars"]

    def test_parse_invalid_command(self):
        """ivreg is not supported -> error message"""
        r = P("ivreg Y X (Z=W)")
        assert r["success"] is False
        assert "Unsupported" in r["error"]

    def test_parse_ologit_warning(self):
        """ologit parses but warns about V3"""
        r = P("ologit Y X c1")
        assert r["success"] is True
        assert r["warning"] is not None
        assert "V3" in r["warning"]
