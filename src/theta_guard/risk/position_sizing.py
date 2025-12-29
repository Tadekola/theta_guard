"""Position sizing advisory calculator.

This module provides advisory position sizing recommendations based on
account size and risk parameters.

IMPORTANT: This is READ-ONLY advisory information.
It does NOT affect the core TRADE ALLOWED / NO TRADE decision.
No orders are placed - this is informational only.

Charter compliance:
- Advisory layer only - no decision override
- Graceful degradation on missing data
- Clear guidance when data is insufficient
"""

from typing import Any
import math


def recommend_position_size(
    account_size: float | None,
    max_risk_pct: float,
    max_loss_per_contract: float | None,
) -> dict[str, Any]:
    """Recommend position size based on account and risk parameters.

    Args:
        account_size: Total account value in dollars.
        max_risk_pct: Maximum risk as decimal (e.g., 0.01 for 1%).
        max_loss_per_contract: Max loss per contract in SPX option units.
            In our system, 1.00 = $100, so multiply by 100 for dollars.

    Returns:
        Dictionary with:
        - contracts: int|None - Recommended number of contracts
        - risk_budget: float|None - Total risk budget in dollars
        - risk_used: float|None - Risk used at recommended size in dollars
        - detail: str - Explanation
        - valid: bool
        - forward_test_note: str|None - Note about forward testing cap
    """
    result: dict[str, Any] = {
        "contracts": None,
        "risk_budget": None,
        "risk_used": None,
        "detail": "",
        "valid": False,
        "forward_test_note": None,
    }

    try:
        if account_size is None or account_size <= 0:
            result["detail"] = (
                "Account size not provided. Enter your account size in the sidebar "
                "to receive position sizing guidance."
            )
            return result

        if max_risk_pct <= 0 or max_risk_pct > 1.0:
            result["detail"] = "Invalid risk percentage. Must be between 0 and 100%."
            return result

        if max_loss_per_contract is None or max_loss_per_contract <= 0:
            result["detail"] = (
                "Max loss per contract unknown. Cannot compute position size "
                "without knowing the maximum risk per spread."
            )
            return result

        dollars_max_loss = max_loss_per_contract * 100.0

        risk_budget = account_size * max_risk_pct

        contracts = math.floor(risk_budget / dollars_max_loss)

        contracts = max(0, contracts)

        risk_used = contracts * dollars_max_loss if contracts > 0 else 0.0

        result["contracts"] = contracts
        result["risk_budget"] = round(risk_budget, 2)
        result["risk_used"] = round(risk_used, 2)
        result["valid"] = True

        result["forward_test_note"] = (
            "⚠️ Advisory: Cap at 1 contract until you have completed at least "
            "8 forward-test weeks with this system."
        )

        if contracts == 0:
            result["detail"] = (
                f"Risk budget ${risk_budget:.2f} is insufficient for the "
                f"${dollars_max_loss:.2f} max loss per contract. Consider "
                "increasing account size or risk tolerance."
            )
        else:
            result["detail"] = (
                f"Based on ${account_size:,.0f} account and {max_risk_pct*100:.1f}% risk, "
                f"you can trade up to {contracts} contract(s). "
                f"Risk budget: ${risk_budget:.2f}, Risk used: ${risk_used:.2f}."
            )

        return result

    except Exception:
        result["detail"] = "Unexpected error computing position size."
        return result


def compute_risk_metrics(
    account_size: float | None,
    max_loss_per_contract: float | None,
    net_premium_per_contract: float | None,
    contracts: int,
) -> dict[str, Any]:
    """Compute additional risk metrics for display.

    Args:
        account_size: Total account value in dollars.
        max_loss_per_contract: Max loss in SPX option units (1.00 = $100).
        net_premium_per_contract: Net premium in SPX option units.
        contracts: Number of contracts being traded.

    Returns:
        Dictionary with risk metrics.
    """
    result: dict[str, Any] = {
        "total_max_loss": None,
        "total_credit": None,
        "account_risk_pct": None,
        "reward_to_risk": None,
        "valid": False,
    }

    try:
        if contracts <= 0:
            return result

        if max_loss_per_contract is not None and max_loss_per_contract > 0:
            total_max_loss = contracts * max_loss_per_contract * 100
            result["total_max_loss"] = round(total_max_loss, 2)

            if account_size is not None and account_size > 0:
                result["account_risk_pct"] = round(
                    (total_max_loss / account_size) * 100, 2
                )

        if net_premium_per_contract is not None:
            total_credit = contracts * net_premium_per_contract * 100
            result["total_credit"] = round(total_credit, 2)

            if result["total_max_loss"] is not None and result["total_max_loss"] > 0:
                result["reward_to_risk"] = round(
                    total_credit / result["total_max_loss"], 2
                )

        result["valid"] = True
        return result

    except Exception:
        return result


if __name__ == "__main__":
    print("=" * 70)
    print("TEST 1: Standard position sizing")
    print("-" * 70)
    result = recommend_position_size(
        account_size=50000.0,
        max_risk_pct=0.01,
        max_loss_per_contract=3.50,
    )
    print(f"  contracts: {result['contracts']}")
    print(f"  risk_budget: ${result['risk_budget']}")
    print(f"  risk_used: ${result['risk_used']}")
    print(f"  detail: {result['detail']}")
    print(f"  forward_test_note: {result['forward_test_note']}")

    print("\n" + "=" * 70)
    print("TEST 2: Small account - may get 0 contracts")
    print("-" * 70)
    result = recommend_position_size(
        account_size=5000.0,
        max_risk_pct=0.005,
        max_loss_per_contract=4.00,
    )
    print(f"  contracts: {result['contracts']}")
    print(f"  risk_budget: ${result['risk_budget']}")
    print(f"  detail: {result['detail']}")

    print("\n" + "=" * 70)
    print("TEST 3: Missing account size")
    print("-" * 70)
    result = recommend_position_size(
        account_size=None,
        max_risk_pct=0.01,
        max_loss_per_contract=3.50,
    )
    print(f"  valid: {result['valid']}")
    print(f"  detail: {result['detail']}")

    print("\n" + "=" * 70)
    print("TEST 4: Missing max loss")
    print("-" * 70)
    result = recommend_position_size(
        account_size=50000.0,
        max_risk_pct=0.01,
        max_loss_per_contract=None,
    )
    print(f"  valid: {result['valid']}")
    print(f"  detail: {result['detail']}")

    print("\n" + "=" * 70)
    print("TEST 5: Risk metrics calculation")
    print("-" * 70)
    metrics = compute_risk_metrics(
        account_size=50000.0,
        max_loss_per_contract=3.50,
        net_premium_per_contract=2.00,
        contracts=1,
    )
    print(f"  total_max_loss: ${metrics['total_max_loss']}")
    print(f"  total_credit: ${metrics['total_credit']}")
    print(f"  account_risk_pct: {metrics['account_risk_pct']}%")
    print(f"  reward_to_risk: {metrics['reward_to_risk']}")
