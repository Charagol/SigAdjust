"""Control variable combination enumeration.

Enumerates all non-empty subsets of control variables using itertools.combinations,
replacing the Stata tuiles.ado workflow (~700 lines) with ~6 lines.
"""

from itertools import combinations


def generate_specs(control_vars: list[str]) -> list[dict]:
    """Enumerate all non-empty subsets of control variables.

    Args:
        control_vars: List of control variable column names.

    Returns:
        List of dicts, each with keys:
          - control_set: list[str] — the subset of control vars
          - spec_label: str — e.g. "c1+c2+c3"
    """
    specs = []
    k = len(control_vars)

    for r in range(1, k + 1):
        for combo in combinations(control_vars, r):
            specs.append({
                "control_set": list(combo),
                "spec_label": "+".join(combo),
            })

    return specs
