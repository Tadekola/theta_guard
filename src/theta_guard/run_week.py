"""End-to-end pipeline orchestrator for THETA-GUARD.

This module wires together existing modules to execute the full
weekly trade evaluation pipeline.

It does NOT contain trading logic, calculations, or rule definitions.
It only coordinates the pipeline and reports results.

Pipeline Order:
1) Holiday Gate
2) EMA Engine
3) Entry Evaluator
4) BWB Builder (only if trade is allowed)
"""

from typing import Any

from theta_guard.calendar.holiday_gate import is_trade_week
from theta_guard.indicators.ema_engine import compute_ema_state
from theta_guard.signals.entry_evaluator import evaluate_entry
from theta_guard.strategies.bwb_builder import build_bwb_structure
from theta_guard.research.event_calendar import get_macro_event_tags

DECISION_TRADE_ALLOWED = "TRADE ALLOWED"


def run_weekly_pipeline(
    monday_date: str,
    entry_time_valid: bool,
    prices: list[float],
    option_chain: list[dict[str, Any]],
    structure_type: str,
) -> dict[str, Any]:
    """Execute the full weekly trade evaluation pipeline.

    Pipeline executes in strict order:
    1) Holiday Gate - Check if week is tradeable
    2) EMA Engine - Compute indicator state
    3) Entry Evaluator - Make trade decision
    4) BWB Builder - Build structure (only if allowed)

    Args:
        monday_date: ISO date string (YYYY-MM-DD) for the Monday of trade week.
        entry_time_valid: Whether entry is within valid time window.
        prices: List of daily closing prices (oldest to newest).
        option_chain: List of option dicts for the target expiration.
        structure_type: "PUT_CREDIT_BWB" or "CALL_DEBIT_BWB"

    Returns:
        Dictionary with exactly these keys:
        - holiday_result: dict - Output from is_trade_week
        - ema_state: dict - Output from compute_ema_state
        - entry_decision: dict - Output from evaluate_entry
        - bwb_structure: dict | None - Output from build_bwb_structure or None
        - spot_proxy: float | None - Latest close price as spot proxy
        - option_chain: list - Option chain passed through for advisory modules
    """
    result: dict[str, Any] = {
        "holiday_result": None,
        "ema_state": None,
        "entry_decision": None,
        "bwb_structure": None,
        "spot_proxy": prices[-1] if prices else None,
        "option_chain": option_chain,
        "macro_events": get_macro_event_tags(monday_date),
    }

    try:
        holiday_result = is_trade_week(monday_date)
        result["holiday_result"] = holiday_result

        ema_state = compute_ema_state(prices)
        result["ema_state"] = ema_state

        entry_context = {
            "entry_day": "Monday",
            "entry_time_valid": entry_time_valid,
        }

        entry_decision = evaluate_entry(holiday_result, ema_state, entry_context)
        result["entry_decision"] = entry_decision

        if entry_decision.get("decision") != DECISION_TRADE_ALLOWED:
            return result

        bwb_structure = build_bwb_structure(option_chain, structure_type)
        result["bwb_structure"] = bwb_structure

        return result

    except Exception:
        if result["entry_decision"] is None:
            result["entry_decision"] = {
                "decision": "NO TRADE",
                "hard_blocks_triggered": ["pipeline_error"],
                "signal_failures": [],
                "reasons": ["Unexpected error in pipeline. Defaulting to NO TRADE."],
            }
        return result


if __name__ == "__main__":
    sample_prices_bullish = [
        5800.0, 5810.0, 5820.0, 5830.0, 5840.0,
        5850.0, 5860.0, 5870.0, 5880.0, 5890.0, 5900.0,
    ]

    sample_prices_bearish = [
        5900.0, 5890.0, 5880.0, 5870.0, 5860.0,
        5850.0, 5840.0, 5830.0, 5820.0, 5810.0, 5800.0,
    ]

    sample_option_chain = [
        {"type": "put", "strike": 5800, "delta": -0.70, "bid": 45.00, "ask": 46.00},
        {"type": "put", "strike": 5825, "delta": -0.65, "bid": 38.00, "ask": 39.00},
        {"type": "put", "strike": 5850, "delta": -0.60, "bid": 32.00, "ask": 33.00},
        {"type": "put", "strike": 5875, "delta": -0.55, "bid": 26.00, "ask": 27.00},
        {"type": "put", "strike": 5900, "delta": -0.50, "bid": 21.00, "ask": 22.00},
        {"type": "put", "strike": 5925, "delta": -0.45, "bid": 17.00, "ask": 18.00},
        {"type": "put", "strike": 5950, "delta": -0.40, "bid": 13.00, "ask": 14.00},
    ]

    def print_result(result: dict[str, Any]) -> None:
        """Print pipeline result in readable format."""
        print("\n  HOLIDAY GATE:")
        hr = result["holiday_result"]
        if hr:
            print(f"    is_trade_week: {hr.get('is_trade_week')}")
            print(f"    reason: {hr.get('reason')}")

        print("\n  EMA STATE:")
        es = result["ema_state"]
        if es:
            print(f"    valid: {es.get('valid')}")
            print(f"    short_above_long: {es.get('short_above_long')}")
            print(f"    long_ema_slope: {es.get('long_ema_slope')}")

        print("\n  ENTRY DECISION:")
        ed = result["entry_decision"]
        if ed:
            print(f"    decision: {ed.get('decision')}")
            print(f"    hard_blocks: {ed.get('hard_blocks_triggered')}")
            print(f"    signal_failures: {ed.get('signal_failures')}")

        print("\n  BWB STRUCTURE:")
        bwb = result["bwb_structure"]
        if bwb:
            print(f"    valid: {bwb.get('valid')}")
            print(f"    net_premium: {bwb.get('net_premium')}")
            print(f"    max_loss: {bwb.get('max_loss')}")
            if bwb.get("legs"):
                print("    legs:")
                for leg in bwb["legs"]:
                    print(f"      {leg['action']} {leg['quantity']}x {leg['type']} @ {leg['strike']}")
        else:
            print("    None (trade blocked)")

    print("=" * 70)
    print("DEMO 1: BLOCKED WEEK - Holiday (MLK Day)")
    print("=" * 70)
    result = run_weekly_pipeline(
        monday_date="2024-01-15",
        entry_time_valid=True,
        prices=sample_prices_bullish,
        option_chain=sample_option_chain,
        structure_type="PUT_CREDIT_BWB",
    )
    print_result(result)

    print("\n" + "=" * 70)
    print("DEMO 2: BLOCKED WEEK - Bearish EMA (slope negative)")
    print("=" * 70)
    result = run_weekly_pipeline(
        monday_date="2024-01-08",
        entry_time_valid=True,
        prices=sample_prices_bearish,
        option_chain=sample_option_chain,
        structure_type="PUT_CREDIT_BWB",
    )
    print_result(result)

    print("\n" + "=" * 70)
    print("DEMO 3: BLOCKED WEEK - Entry time invalid")
    print("=" * 70)
    result = run_weekly_pipeline(
        monday_date="2024-01-08",
        entry_time_valid=False,
        prices=sample_prices_bullish,
        option_chain=sample_option_chain,
        structure_type="PUT_CREDIT_BWB",
    )
    print_result(result)

    print("\n" + "=" * 70)
    print("DEMO 4: SUCCESSFUL WEEK - Trade Allowed + BWB Built")
    print("=" * 70)
    result = run_weekly_pipeline(
        monday_date="2024-01-08",
        entry_time_valid=True,
        prices=sample_prices_bullish,
        option_chain=sample_option_chain,
        structure_type="PUT_CREDIT_BWB",
    )
    print_result(result)
