"""Historical Options Outcome Engine for REAL P&L computation.

This module computes REAL historical outcomes using actual
SPX option settlement prices.

It does NOT simulate, optimize, or modify strategy rules.
Results are deterministic and auditable.
"""

from typing import Any

from theta_guard.strategies.bwb_builder import build_bwb_structure
from theta_guard.backtest.evaluator import evaluate_backtest

DECISION_TRADE_ALLOWED = "TRADE ALLOWED"


def evaluate_historical_outcomes(
    weekly_decisions: list[dict[str, Any]],
    monday_chains: dict[str, list[dict[str, Any]]],
    friday_chains: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Evaluate real P&L outcomes for historical weeks.

    Args:
        weekly_decisions: List of decision records with keys:
            - monday_date: str (YYYY-MM-DD)
            - week: str (YYYY-WW)
            - decision: str
            - structure_type: str
        monday_chains: Dict mapping monday_date to Monday option chain snapshot
        friday_chains: Dict mapping monday_date to Friday option chain snapshot

    Returns:
        Dictionary with:
        - metrics: dict - Output from evaluate_backtest
        - weekly_records: list[dict] - All weekly outcome records
    """
    result: dict[str, Any] = {
        "metrics": {},
        "weekly_records": [],
    }

    try:
        weekly_records = []

        for decision_record in weekly_decisions:
            record = _evaluate_single_week(
                decision_record=decision_record,
                monday_chains=monday_chains,
                friday_chains=friday_chains,
            )
            weekly_records.append(record)

        result["weekly_records"] = weekly_records
        result["metrics"] = evaluate_backtest(weekly_records)

        return result

    except Exception:
        return result


def _evaluate_single_week(
    decision_record: dict[str, Any],
    monday_chains: dict[str, list[dict[str, Any]]],
    friday_chains: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Evaluate a single week's outcome with real option data.

    Returns:
        Weekly record with real P&L
    """
    monday_date = decision_record.get("monday_date", "")
    week_label = decision_record.get("week", "")
    decision = decision_record.get("decision", "NO TRADE")
    structure_type = decision_record.get("structure_type", "PUT_CREDIT_BWB")

    record: dict[str, Any] = {
        "week": week_label,
        "decision": decision,
        "structure_type": structure_type if decision == DECISION_TRADE_ALLOWED else None,
        "outcome": "SKIPPED",
        "pnl": 0.0,
        "max_loss": None,
    }

    if decision != DECISION_TRADE_ALLOWED:
        return record

    monday_chain = monday_chains.get(monday_date)
    friday_chain = friday_chains.get(monday_date)

    if not monday_chain:
        record["outcome"] = "SKIPPED"
        return record

    if not friday_chain:
        record["outcome"] = "SKIPPED"
        return record

    bwb_result = build_bwb_structure(monday_chain, structure_type)

    if not bwb_result.get("valid", False):
        record["outcome"] = "SKIPPED"
        return record

    legs = bwb_result.get("legs", [])
    net_premium = bwb_result.get("net_premium", 0.0)
    max_loss = bwb_result.get("max_loss")

    record["max_loss"] = max_loss

    total_pnl = _compute_expiration_pnl(legs, friday_chain, net_premium)

    if total_pnl is None:
        record["outcome"] = "SKIPPED"
        return record

    record["pnl"] = round(total_pnl, 4)
    record["outcome"] = "WIN" if total_pnl >= 0 else "LOSS"

    return record


def _compute_expiration_pnl(
    legs: list[dict[str, Any]],
    friday_chain: list[dict[str, Any]],
    net_premium: float,
) -> float | None:
    """Compute P&L at expiration using settlement prices.

    For each leg:
    - Find matching option in Friday chain
    - Get settlement price
    - Compute payoff based on position (BUY/SELL)

    Args:
        legs: List of leg dicts from BWB structure
        friday_chain: Friday option chain with settlement prices
        net_premium: Net premium received/paid at entry

    Returns:
        Total P&L or None if data missing
    """
    friday_lookup = _build_option_lookup(friday_chain)

    total_leg_value = 0.0

    for leg in legs:
        option_type = leg.get("type")
        strike = leg.get("strike")
        action = leg.get("action")
        quantity = leg.get("quantity", 1)
        entry_price = leg.get("price", 0.0)

        lookup_key = (option_type, strike)
        friday_option = friday_lookup.get(lookup_key)

        if friday_option is None:
            return None

        settlement_price = friday_option.get("settlement_price")
        if settlement_price is None:
            return None

        if action == "SELL":
            leg_pnl = (entry_price - settlement_price) * quantity
        else:
            leg_pnl = (settlement_price - entry_price) * quantity

        total_leg_value += leg_pnl

    total_pnl = total_leg_value + net_premium

    return total_pnl


def _build_option_lookup(
    option_chain: list[dict[str, Any]],
) -> dict[tuple[str, float], dict[str, Any]]:
    """Build lookup dict keyed by (type, strike)."""
    lookup: dict[tuple[str, float], dict[str, Any]] = {}

    for opt in option_chain:
        option_type = opt.get("type")
        strike = opt.get("strike")
        if option_type and strike is not None:
            lookup[(option_type, strike)] = opt

    return lookup


if __name__ == "__main__":
    monday_chain_win = [
        {"type": "put", "strike": 5800, "delta": -0.70, "bid": 45.00, "ask": 46.00},
        {"type": "put", "strike": 5825, "delta": -0.65, "bid": 38.00, "ask": 39.00},
        {"type": "put", "strike": 5850, "delta": -0.60, "bid": 32.00, "ask": 33.00},
        {"type": "put", "strike": 5875, "delta": -0.55, "bid": 26.00, "ask": 27.00},
        {"type": "put", "strike": 5900, "delta": -0.50, "bid": 21.00, "ask": 22.00},
        {"type": "put", "strike": 5925, "delta": -0.45, "bid": 17.00, "ask": 18.00},
        {"type": "put", "strike": 5950, "delta": -0.40, "bid": 13.00, "ask": 14.00},
    ]

    friday_chain_win = [
        {"type": "put", "strike": 5800, "settlement_price": 0.00},
        {"type": "put", "strike": 5825, "settlement_price": 0.00},
        {"type": "put", "strike": 5850, "settlement_price": 0.00},
        {"type": "put", "strike": 5875, "settlement_price": 0.00},
        {"type": "put", "strike": 5900, "settlement_price": 0.05},
        {"type": "put", "strike": 5925, "settlement_price": 0.10},
        {"type": "put", "strike": 5950, "settlement_price": 0.15},
    ]

    friday_chain_loss = [
        {"type": "put", "strike": 5800, "settlement_price": 0.00},
        {"type": "put", "strike": 5825, "settlement_price": 0.00},
        {"type": "put", "strike": 5850, "settlement_price": 15.00},
        {"type": "put", "strike": 5875, "settlement_price": 40.00},
        {"type": "put", "strike": 5900, "settlement_price": 65.00},
        {"type": "put", "strike": 5925, "settlement_price": 90.00},
        {"type": "put", "strike": 5950, "settlement_price": 115.00},
    ]

    weekly_decisions = [
        {
            "monday_date": "2024-01-08",
            "week": "2024-W02",
            "decision": "TRADE ALLOWED",
            "structure_type": "PUT_CREDIT_BWB",
        },
        {
            "monday_date": "2024-01-15",
            "week": "2024-W03",
            "decision": "NO TRADE",
            "structure_type": "PUT_CREDIT_BWB",
        },
        {
            "monday_date": "2024-01-22",
            "week": "2024-W04",
            "decision": "TRADE ALLOWED",
            "structure_type": "PUT_CREDIT_BWB",
        },
    ]

    monday_chains = {
        "2024-01-08": monday_chain_win,
        "2024-01-22": monday_chain_win,
    }

    friday_chains = {
        "2024-01-08": friday_chain_win,
        "2024-01-22": friday_chain_loss,
    }

    print("=" * 70)
    print("HISTORICAL OPTIONS OUTCOME ENGINE - Real P&L Demo")
    print("=" * 70)

    print("\nSTEP 1: Build BWB structure from Monday chain")
    print("-" * 70)
    bwb = build_bwb_structure(monday_chain_win, "PUT_CREDIT_BWB")
    print(f"  Structure valid: {bwb['valid']}")
    print(f"  Net premium: {bwb['net_premium']}")
    print(f"  Max loss: {bwb['max_loss']}")
    print("  Legs:")
    for leg in bwb["legs"]:
        print(f"    {leg['action']} {leg['quantity']}x {leg['type']} @ {leg['strike']} for {leg['price']}")

    print("\nSTEP 2: Compute P&L at expiration (WINNING week)")
    print("-" * 70)
    print("  Friday settlement: All puts expire near worthless (SPX closed above strikes)")
    pnl_win = _compute_expiration_pnl(bwb["legs"], friday_chain_win, bwb["net_premium"])
    print(f"  Computed P&L: {pnl_win:+.2f}")
    print("  Explanation: Premium collected, options expired worthless → WIN")

    print("\nSTEP 3: Compute P&L at expiration (LOSING week)")
    print("-" * 70)
    print("  Friday settlement: SPX dropped significantly, puts have intrinsic value")
    pnl_loss = _compute_expiration_pnl(bwb["legs"], friday_chain_loss, bwb["net_premium"])
    print(f"  Computed P&L: {pnl_loss:+.2f}")
    print("  Explanation: Short puts went ITM → LOSS")

    print("\n" + "=" * 70)
    print("FULL EVALUATION - 3 Weeks")
    print("=" * 70)

    result = evaluate_historical_outcomes(
        weekly_decisions=weekly_decisions,
        monday_chains=monday_chains,
        friday_chains=friday_chains,
    )

    print("\nWEEKLY RECORDS:")
    print("-" * 70)
    for record in result["weekly_records"]:
        status = f"{record['decision']:14} | {record['outcome']:7} | PnL: {record['pnl']:+8.2f}"
        print(f"  {record['week']}: {status}")

    print("\nMETRICS:")
    print("-" * 70)
    for key, value in result["metrics"].items():
        if isinstance(value, float):
            print(f"  {key}: {value:+.4f}")
        else:
            print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("P&L MATH VERIFICATION (Winning Week)")
    print("=" * 70)
    print("\n  Structure: PUT Credit BWB")
    print("  Short strike: 5875 (x2)")
    print("  Long upper: 5900")
    print("  Long lower: 5825")
    print("\n  Entry prices (mid):")
    print("    SELL 2x 5875 put @ 26.50 = +53.00")
    print("    BUY 1x 5900 put @ 21.50 = -21.50")
    print("    BUY 1x 5825 put @ 38.50 = -38.50")
    print("    Net premium = +53.00 - 21.50 - 38.50 = -7.00 (debit)")
    print("\n  Expiration (all near zero):")
    print("    Short 5875: entry 26.50 - settlement 0.00 = +26.50 x2 = +53.00")
    print("    Long 5900: settlement 0.05 - entry 21.50 = -21.45")
    print("    Long 5825: settlement 0.00 - entry 38.50 = -38.50")
    print("    Leg value = +53.00 - 21.45 - 38.50 = -6.95")
    print(f"\n  Total P&L = leg_value + net_premium = -6.95 + (-7.00) = {pnl_win:+.2f}")
