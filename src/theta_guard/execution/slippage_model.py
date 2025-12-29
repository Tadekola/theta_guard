"""Slippage and Fill Assumption Model.

This module provides analytical tools for understanding how slippage
affects trade outcomes. It is purely advisory and does NOT affect
trade decisions.

All calculations assume:
- net_premium and max_loss are in SPX option price units (1.00 = $100)
- slippage_pct is a decimal (e.g., 0.05 = 5%)
"""

from typing import Any


DEFAULT_SLIPPAGE_PCTS = [0.0, 0.05, 0.10, 0.15]


def apply_slippage(
    net_premium: float | None,
    max_loss: float | None,
    slippage_pct: float = 0.05,
) -> dict[str, Any]:
    """Apply slippage to premium and max loss calculations.

    Slippage reduces the credit received and increases max loss by the
    same amount (the "slippage cost").

    Args:
        net_premium: Net credit received in option price units (1.00 = $100).
        max_loss: Maximum loss per spread in option price units.
        slippage_pct: Slippage as decimal (0.05 = 5%).

    Returns:
        Dictionary with original and adjusted values.
    """
    result: dict[str, Any] = {
        "slippage_pct": slippage_pct,
        "credit_mid": None,
        "credit_adjusted": None,
        "max_loss_mid": None,
        "max_loss_adjusted": None,
        "valid": False,
    }

    try:
        if net_premium is None or max_loss is None:
            return result

        if not isinstance(net_premium, (int, float)) or not isinstance(max_loss, (int, float)):
            return result

        if slippage_pct < 0 or slippage_pct > 1:
            slippage_pct = max(0.0, min(1.0, slippage_pct))

        credit_mid = float(net_premium)
        max_loss_mid = float(max_loss)

        credit_adjusted = credit_mid * (1 - slippage_pct)
        slippage_cost = credit_mid - credit_adjusted
        max_loss_adjusted = max_loss_mid + slippage_cost

        result["credit_mid"] = round(credit_mid, 4)
        result["credit_adjusted"] = round(credit_adjusted, 4)
        result["max_loss_mid"] = round(max_loss_mid, 4)
        result["max_loss_adjusted"] = round(max_loss_adjusted, 4)
        result["valid"] = True

        return result

    except Exception:
        return result


def compute_slippage_analysis(
    net_premium: float | None,
    max_loss: float | None,
    slippage_pcts: list[float] | None = None,
) -> dict[str, Any]:
    """Compute slippage analysis for multiple slippage percentages.

    Args:
        net_premium: Net credit in option price units.
        max_loss: Maximum loss in option price units.
        slippage_pcts: List of slippage percentages to analyze.

    Returns:
        Dictionary mapping slippage_pct to analysis result.
    """
    if slippage_pcts is None:
        slippage_pcts = DEFAULT_SLIPPAGE_PCTS

    analysis: dict[str, Any] = {
        "scenarios": {},
        "valid": False,
    }

    try:
        if net_premium is None or max_loss is None:
            return analysis

        all_valid = True
        for pct in slippage_pcts:
            result = apply_slippage(net_premium, max_loss, pct)
            key = f"{int(pct * 100)}pct"
            analysis["scenarios"][key] = result
            if not result.get("valid"):
                all_valid = False

        analysis["valid"] = all_valid and len(analysis["scenarios"]) > 0
        return analysis

    except Exception:
        return analysis


def format_slippage_table(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Format slippage analysis as a table for display.

    Args:
        analysis: Output from compute_slippage_analysis.

    Returns:
        List of row dictionaries for table display.
    """
    rows = []

    try:
        scenarios = analysis.get("scenarios", {})

        for key in ["0pct", "5pct", "10pct", "15pct"]:
            scenario = scenarios.get(key, {})

            pct = scenario.get("slippage_pct", 0)
            credit = scenario.get("credit_adjusted")
            max_loss = scenario.get("max_loss_adjusted")

            rows.append({
                "slippage": f"{int(pct * 100)}%",
                "credit": f"${credit * 100:.2f}" if credit is not None else "N/A",
                "max_loss": f"${max_loss * 100:.2f}" if max_loss is not None else "N/A",
            })

        return rows

    except Exception:
        return []


if __name__ == "__main__":
    print("=== Slippage Model Test ===\n")

    net_premium = 2.50
    max_loss = 3.50

    print(f"Input: net_premium={net_premium}, max_loss={max_loss}")
    print()

    for pct in DEFAULT_SLIPPAGE_PCTS:
        result = apply_slippage(net_premium, max_loss, pct)
        print(f"Slippage {int(pct*100)}%:")
        print(f"  Credit: ${result['credit_mid']*100:.2f} -> ${result['credit_adjusted']*100:.2f}")
        print(f"  Max Loss: ${result['max_loss_mid']*100:.2f} -> ${result['max_loss_adjusted']*100:.2f}")
        print()

    print("=== Full Analysis ===")
    analysis = compute_slippage_analysis(net_premium, max_loss)
    print(f"Valid: {analysis['valid']}")
    print(f"Scenarios: {list(analysis['scenarios'].keys())}")
    print()

    print("=== Formatted Table ===")
    table = format_slippage_table(analysis)
    for row in table:
        print(f"  {row['slippage']:>4} | Credit: {row['credit']:>10} | Max Loss: {row['max_loss']:>10}")
