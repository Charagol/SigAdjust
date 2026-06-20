"""Stata command parser — pure logic, no Qt dependency.

Parses Stata regression commands into structured data for form filling.
Supports: reg/regress, logit, probit, ologit, oprobit, reghdfe.
Detects: i.varname factor variables, robust/vce options, absorb().

Usage:
    result = StataCommandParser.parse("reg Y X c1 c2, robust")
    # result = {
    #     "success": True,
    #     "model_type": "ols",
    #     "dependent_var": "Y",
    #     "key_var": "X",
    #     "control_vars": ["c1", "c2"],
    #     "factor_vars": [],
    #     "fe_vars": [],
    #     "se_type": "robust",
    # }
"""

import re
from typing import Optional


COMMAND_MAP = {
    "reg": "ols",
    "regress": "ols",
    "logit": "logit",
    "probit": "probit",
    "ologit": "ologit",
    "oprobit": "oprobit",
    "reghdfe": "fe",
}

UNSUPPORTED_MSG = (
    "Supported commands: reg, logit, probit, ologit, oprobit, reghdfe"
)


class StataCommandParser:
    """Pure-logic parser for Stata regression commands.

    This class has zero UI dependencies and is independently testable.
    """

    @staticmethod
    def parse(command_text: str) -> dict:
        """Parse a Stata regression command string.

        Args:
            command_text: Raw command string, e.g. "reg Y X c1 c2, robust"

        Returns:
            Dict with keys: success, error, warning, model_type,
            dependent_var, key_var, control_vars, factor_vars,
            fe_vars, se_type
        """
        result = {
            "success": False,
            "error": None,
            "warning": None,
            "model_type": None,
            "dependent_var": None,
            "key_var": None,
            "control_vars": [],
            "factor_vars": [],
            "fe_vars": [],
            "se_type": "default",
        }

        text = command_text.strip()
        if not text:
            result["error"] = "Empty command."
            return result

        # Step 1: Split command and options at the first comma
        parts = text.split(",", 1)
        cmd_part = parts[0].strip()
        opts_part = parts[1].strip() if len(parts) > 1 else ""

        # Step 2: Identify command
        tokens = cmd_part.split()
        if not tokens:
            result["error"] = "Empty command."
            return result

        raw_cmd = tokens[0].lower()
        if raw_cmd not in COMMAND_MAP:
            result["error"] = f"Unsupported command: [{raw_cmd}]. {UNSUPPORTED_MSG}"
            return result

        model_type = COMMAND_MAP[raw_cmd]

        # ologit/oprobit: parse but warn
        if raw_cmd in ("ologit", "oprobit"):
            result["warning"] = (
                "Ordered choice models are not yet supported and "
                "will be implemented in V3."
            )

        result["model_type"] = model_type if model_type != "ologit" else "logit"
        if raw_cmd == "oprobit":
            result["model_type"] = "probit"

        # Step 3: Extract variables
        var_tokens = tokens[1:]  # Skip command
        if not var_tokens:
            result["error"] = "No variables found. Expected: cmd depvar keyvar [controls]"
            return result

        result["dependent_var"] = var_tokens[0]
        if len(var_tokens) >= 2:
            result["key_var"] = var_tokens[1]
        else:
            result["key_var"] = ""

        # Rest are control variables + i.xxx factor vars
        raw_controls = var_tokens[2:] if len(var_tokens) > 2 else []
        bare_controls = []
        factor_vars = []

        for tok in raw_controls:
            if tok.startswith("i."):
                fv = tok[2:]  # Strip "i." prefix
                if fv:
                    factor_vars.append(fv)
            else:
                bare_controls.append(tok)

        result["control_vars"] = bare_controls
        result["factor_vars"] = factor_vars

        # Step 4: Parse reghdfe absorb()
        if raw_cmd == "reghdfe":
            absorb_match = re.search(r"absorb\(([^)]+)\)", opts_part, re.IGNORECASE)
            if not absorb_match:
                result["error"] = "reghdfe requires absorb()."
                return result
            absorb_content = absorb_match.group(1).strip()
            # Split by whitespace to get individual FE vars
            fe_tokens = absorb_content.split()
            fe_vars = []
            for ft in fe_tokens:
                ft = ft.strip()
                if ft.startswith("i."):
                    ft = ft[2:]
                if ft:
                    fe_vars.append(ft)
            result["fe_vars"] = fe_vars

        # Step 5: Parse options (robust, vce, cluster)
        if opts_part:
            opts_lower = opts_part.lower()
            if re.search(r"\brobust\b|\br\b", opts_lower):
                result["se_type"] = "robust"
            elif re.search(r"vce\(robust\)", opts_lower):
                result["se_type"] = "robust"
            elif re.search(r"vce\(cluster\b", opts_lower):
                result["error"] = (
                    "Clustered standard errors are not supported. "
                    "Use robust or default standard errors."
                )
                return result

        result["success"] = True
        return result
