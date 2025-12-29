"""Entry evaluator for assessing trade entry conditions.

This module is the decision engine that determines whether a trade
is allowed to be entered for a given week.

It strictly follows the Trading Charter priority:
1) HARD BLOCKS (Section 3) - Always override signals
2) SIGNAL CONDITIONS (Section 4) - Required but not sufficient
3) FINAL DECISION

Charter compliance:
- Section 3: Hard block rules trigger NO TRADE
- Section 4: Signal conditions must all pass
- Section 7: No discretion clause - if conditions not met, NO TRADE
- Section 8: Binary decision output
"""

from typing import Any

DECISION_TRADE_ALLOWED = "TRADE ALLOWED"
DECISION_NO_TRADE = "NO TRADE"


def evaluate_entry(
    holiday_result: dict[str, Any],
    ema_state: dict[str, Any],
    entry_context: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate whether a trade entry is permitted.

    Applies hard block rules first, then signal conditions.
    Hard blocks always override signals.

    Args:
        holiday_result: Output from is_trade_week (holiday_gate module).
            Expected keys: is_trade_week, reason
        ema_state: Output from compute_ema_state (ema_engine module).
            Expected keys: valid, short_above_long, long_ema_slope, reason
        entry_context: Contextual metadata for entry.
            Expected keys: entry_day, entry_time_valid

    Returns:
        Dictionary with exactly these keys:
        - decision: "TRADE ALLOWED" | "NO TRADE"
        - hard_blocks_triggered: list[str] - Names of triggered hard blocks
        - signal_failures: list[str] - Names of failed signal conditions
        - reasons: list[str] - Human-readable explanations
    """
    result: dict[str, Any] = {
        "decision": DECISION_NO_TRADE,
        "hard_blocks_triggered": [],
        "signal_failures": [],
        "reasons": [],
    }

    try:
        hard_blocks = _evaluate_hard_blocks(holiday_result, ema_state, entry_context)
        result["hard_blocks_triggered"] = hard_blocks["triggered"]
        result["reasons"].extend(hard_blocks["reasons"])

        if hard_blocks["triggered"]:
            result["decision"] = DECISION_NO_TRADE
            return result

        signal_failures = _evaluate_signal_conditions(ema_state)
        result["signal_failures"] = signal_failures["failed"]
        result["reasons"].extend(signal_failures["reasons"])

        if signal_failures["failed"]:
            result["decision"] = DECISION_NO_TRADE
            return result

        result["decision"] = DECISION_TRADE_ALLOWED
        result["reasons"].append("All hard blocks cleared and signal conditions met.")
        return result

    except Exception:
        result["decision"] = DECISION_NO_TRADE
        result["hard_blocks_triggered"].append("evaluation_error")
        result["reasons"].append(
            "Unexpected error during evaluation. Defaulting to NO TRADE."
        )
        return result


def _evaluate_hard_blocks(
    holiday_result: dict[str, Any],
    ema_state: dict[str, Any],
    entry_context: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate all hard block conditions.

    Returns:
        Dictionary with:
        - triggered: list[str] - Names of triggered hard blocks
        - reasons: list[str] - Explanations for each triggered block
    """
    triggered: list[str] = []
    reasons: list[str] = []

    if not isinstance(holiday_result, dict):
        triggered.append("holiday_data_invalid")
        reasons.append("HARD BLOCK: Holiday result is missing or malformed.")
    elif not holiday_result.get("is_trade_week", False):
        triggered.append("holiday_block")
        holiday_reason = holiday_result.get("reason", "Holiday check failed.")
        reasons.append(f"HARD BLOCK: {holiday_reason}")

    if not isinstance(entry_context, dict):
        triggered.append("entry_context_invalid")
        reasons.append("HARD BLOCK: Entry context is missing or malformed.")
    elif not entry_context.get("entry_time_valid", False):
        triggered.append("entry_time_invalid")
        reasons.append("HARD BLOCK: Entry time is outside the valid window.")

    if not isinstance(ema_state, dict):
        triggered.append("ema_data_invalid")
        reasons.append("HARD BLOCK: EMA state is missing or malformed.")
    elif not ema_state.get("valid", False):
        triggered.append("ema_invalid")
        ema_reason = ema_state.get("reason", "EMA data is invalid.")
        reasons.append(f"HARD BLOCK: {ema_reason}")

    return {"triggered": triggered, "reasons": reasons}


def _evaluate_signal_conditions(ema_state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate signal conditions after hard blocks pass.

    Returns:
        Dictionary with:
        - failed: list[str] - Names of failed signal conditions
        - reasons: list[str] - Explanations for each failure
    """
    failed: list[str] = []
    reasons: list[str] = []

    short_above_long = ema_state.get("short_above_long", False)
    if not short_above_long:
        failed.append("short_ema_not_above_long")
        reasons.append(
            "SIGNAL FAIL: 3-period EMA is not above 8-period EMA."
        )

    long_ema_slope = ema_state.get("long_ema_slope", "negative")
    if long_ema_slope == "negative":
        failed.append("long_ema_slope_negative")
        reasons.append(
            "SIGNAL FAIL: 8-period EMA slope is negative."
        )

    return {"failed": failed, "reasons": reasons}


if __name__ == "__main__":
    print("=" * 70)
    print("TEST 1: Holiday block → NO TRADE")
    print("-" * 70)
    result = evaluate_entry(
        holiday_result={"is_trade_week": False, "reason": "Monday is a market holiday."},
        ema_state={"valid": True, "short_above_long": True, "long_ema_slope": "positive"},
        entry_context={"entry_day": "Monday", "entry_time_valid": True},
    )
    print(f"  decision: {result['decision']}")
    print(f"  hard_blocks_triggered: {result['hard_blocks_triggered']}")
    print(f"  signal_failures: {result['signal_failures']}")
    print(f"  reasons: {result['reasons']}")

    print("\n" + "=" * 70)
    print("TEST 2: EMA invalid → NO TRADE")
    print("-" * 70)
    result = evaluate_entry(
        holiday_result={"is_trade_week": True, "reason": "Trade week allowed."},
        ema_state={"valid": False, "reason": "Insufficient data for EMA calculation."},
        entry_context={"entry_day": "Monday", "entry_time_valid": True},
    )
    print(f"  decision: {result['decision']}")
    print(f"  hard_blocks_triggered: {result['hard_blocks_triggered']}")
    print(f"  signal_failures: {result['signal_failures']}")
    print(f"  reasons: {result['reasons']}")

    print("\n" + "=" * 70)
    print("TEST 3: EMA valid but slope negative → NO TRADE")
    print("-" * 70)
    result = evaluate_entry(
        holiday_result={"is_trade_week": True, "reason": "Trade week allowed."},
        ema_state={
            "valid": True,
            "short_above_long": True,
            "long_ema_slope": "negative",
            "reason": "EMA computed.",
        },
        entry_context={"entry_day": "Monday", "entry_time_valid": True},
    )
    print(f"  decision: {result['decision']}")
    print(f"  hard_blocks_triggered: {result['hard_blocks_triggered']}")
    print(f"  signal_failures: {result['signal_failures']}")
    print(f"  reasons: {result['reasons']}")

    print("\n" + "=" * 70)
    print("TEST 4: All conditions met → TRADE ALLOWED")
    print("-" * 70)
    result = evaluate_entry(
        holiday_result={"is_trade_week": True, "reason": "Trade week allowed."},
        ema_state={
            "valid": True,
            "short_above_long": True,
            "long_ema_slope": "positive",
            "reason": "EMA computed.",
        },
        entry_context={"entry_day": "Monday", "entry_time_valid": True},
    )
    print(f"  decision: {result['decision']}")
    print(f"  hard_blocks_triggered: {result['hard_blocks_triggered']}")
    print(f"  signal_failures: {result['signal_failures']}")
    print(f"  reasons: {result['reasons']}")

    print("\n" + "=" * 70)
    print("TEST 5: Entry time invalid → NO TRADE")
    print("-" * 70)
    result = evaluate_entry(
        holiday_result={"is_trade_week": True, "reason": "Trade week allowed."},
        ema_state={
            "valid": True,
            "short_above_long": True,
            "long_ema_slope": "positive",
            "reason": "EMA computed.",
        },
        entry_context={"entry_day": "Monday", "entry_time_valid": False},
    )
    print(f"  decision: {result['decision']}")
    print(f"  hard_blocks_triggered: {result['hard_blocks_triggered']}")
    print(f"  signal_failures: {result['signal_failures']}")
    print(f"  reasons: {result['reasons']}")
