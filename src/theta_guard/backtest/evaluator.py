"""Evaluator for backtesting strategy performance.

This module evaluates historical performance using PRECOMPUTED inputs only.
It does NOT influence live trading decisions.

It exists for analysis and confidence measurement only.
"""

from typing import Any

DECISION_TRADE_ALLOWED = "TRADE ALLOWED"
OUTCOME_WIN = "WIN"
OUTCOME_LOSS = "LOSS"
OUTCOME_SKIPPED = "SKIPPED"


def evaluate_backtest(weekly_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate backtest performance from precomputed weekly results.

    Args:
        weekly_results: List of weekly trade records. Each record must contain:
            - week: str - Week identifier
            - decision: "TRADE ALLOWED" | "NO TRADE"
            - net_premium: float | None
            - max_loss: float | None
            - outcome: "WIN" | "LOSS" | "SKIPPED"
            - pnl: float - Authoritative P&L for the week

    Returns:
        Dictionary with exactly these keys:
        - total_trades: int
        - wins: int
        - losses: int
        - win_rate: float
        - average_win: float
        - average_loss: float
        - expectancy: float
        - cumulative_pnl: float
        - max_drawdown: float
        - return_on_risk: float
    """
    result = _empty_result()

    try:
        if not isinstance(weekly_results, list) or len(weekly_results) == 0:
            return result

        traded_weeks = _filter_traded_weeks(weekly_results)
        if not traded_weeks:
            return result

        wins = [w for w in traded_weeks if w.get("outcome") == OUTCOME_WIN]
        losses = [w for w in traded_weeks if w.get("outcome") == OUTCOME_LOSS]

        total_trades = len(traded_weeks)
        win_count = len(wins)
        loss_count = len(losses)

        win_pnls = [w.get("pnl", 0.0) for w in wins]
        loss_pnls = [w.get("pnl", 0.0) for w in losses]
        all_pnls = [w.get("pnl", 0.0) for w in traded_weeks]
        max_losses = [w.get("max_loss") for w in traded_weeks if w.get("max_loss") is not None]

        win_rate = win_count / total_trades if total_trades > 0 else 0.0
        average_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
        average_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0.0
        expectancy = sum(all_pnls) / len(all_pnls) if all_pnls else 0.0
        cumulative_pnl = sum(all_pnls)

        max_drawdown = _compute_max_drawdown(all_pnls)

        avg_max_loss = sum(max_losses) / len(max_losses) if max_losses else 0.0
        return_on_risk = expectancy / avg_max_loss if avg_max_loss > 0 else 0.0

        result["total_trades"] = total_trades
        result["wins"] = win_count
        result["losses"] = loss_count
        result["win_rate"] = round(win_rate, 4)
        result["average_win"] = round(average_win, 4)
        result["average_loss"] = round(average_loss, 4)
        result["expectancy"] = round(expectancy, 4)
        result["cumulative_pnl"] = round(cumulative_pnl, 4)
        result["max_drawdown"] = round(max_drawdown, 4)
        result["return_on_risk"] = round(return_on_risk, 4)

        return result

    except Exception:
        return _empty_result()


def _empty_result() -> dict[str, Any]:
    """Return a result dictionary with all metrics set to zero."""
    return {
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "average_win": 0.0,
        "average_loss": 0.0,
        "expectancy": 0.0,
        "cumulative_pnl": 0.0,
        "max_drawdown": 0.0,
        "return_on_risk": 0.0,
    }


def _filter_traded_weeks(
    weekly_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filter to only weeks where trade was allowed and not skipped."""
    return [
        w for w in weekly_results
        if w.get("decision") == DECISION_TRADE_ALLOWED
        and w.get("outcome") != OUTCOME_SKIPPED
    ]


def _compute_max_drawdown(pnls: list[float]) -> float:
    """Compute maximum drawdown (peak-to-trough) from P&L series.

    Args:
        pnls: List of individual trade P&Ls in chronological order.

    Returns:
        Maximum drawdown as a positive number (or 0 if no drawdown).
    """
    if not pnls:
        return 0.0

    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0

    for pnl in pnls:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > max_dd:
            max_dd = drawdown

    return max_dd


if __name__ == "__main__":
    synthetic_data = [
        {"week": "2024-01-08", "decision": "TRADE ALLOWED", "net_premium": 2.50, "max_loss": 22.50, "outcome": "WIN", "pnl": 2.50},
        {"week": "2024-01-15", "decision": "NO TRADE", "net_premium": None, "max_loss": None, "outcome": "SKIPPED", "pnl": 0.0},
        {"week": "2024-01-22", "decision": "TRADE ALLOWED", "net_premium": 2.75, "max_loss": 22.25, "outcome": "WIN", "pnl": 2.75},
        {"week": "2024-01-29", "decision": "TRADE ALLOWED", "net_premium": 2.60, "max_loss": 22.40, "outcome": "LOSS", "pnl": -22.40},
        {"week": "2024-02-05", "decision": "TRADE ALLOWED", "net_premium": 2.80, "max_loss": 22.20, "outcome": "WIN", "pnl": 2.80},
        {"week": "2024-02-12", "decision": "TRADE ALLOWED", "net_premium": 2.55, "max_loss": 22.45, "outcome": "WIN", "pnl": 2.55},
        {"week": "2024-02-19", "decision": "NO TRADE", "net_premium": None, "max_loss": None, "outcome": "SKIPPED", "pnl": 0.0},
        {"week": "2024-02-26", "decision": "TRADE ALLOWED", "net_premium": 2.65, "max_loss": 22.35, "outcome": "WIN", "pnl": 2.65},
        {"week": "2024-03-04", "decision": "TRADE ALLOWED", "net_premium": 2.70, "max_loss": 22.30, "outcome": "LOSS", "pnl": -22.30},
        {"week": "2024-03-11", "decision": "TRADE ALLOWED", "net_premium": 2.45, "max_loss": 22.55, "outcome": "WIN", "pnl": 2.45},
    ]

    print("=" * 70)
    print("BACKTEST EVALUATION - Synthetic Data")
    print("=" * 70)
    print("\nInput Data:")
    print("-" * 70)
    for record in synthetic_data:
        status = f"{record['decision']:14} | {record['outcome']:7} | PnL: {record['pnl']:+7.2f}"
        print(f"  {record['week']}: {status}")

    print("\n" + "=" * 70)
    print("Evaluation Results:")
    print("-" * 70)
    result = evaluate_backtest(synthetic_data)
    for key, value in result.items():
        if isinstance(value, float):
            print(f"  {key}: {value:+.4f}")
        else:
            print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("Drawdown Demonstration:")
    print("-" * 70)
    traded_pnls = [2.50, 2.75, -22.40, 2.80, 2.55, 2.65, -22.30, 2.45]
    cumulative = 0.0
    peak = 0.0
    print("  Trade | PnL     | Cumulative | Peak    | Drawdown")
    print("  " + "-" * 50)
    for i, pnl in enumerate(traded_pnls, 1):
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        print(f"  {i:5} | {pnl:+7.2f} | {cumulative:+10.2f} | {peak:+7.2f} | {dd:+8.2f}")

    print("\n" + "=" * 70)
    print("Edge Cases:")
    print("-" * 70)

    print("\n  Empty input:")
    empty_result = evaluate_backtest([])
    print(f"    total_trades: {empty_result['total_trades']}")
    print(f"    expectancy: {empty_result['expectancy']}")

    print("\n  All skipped weeks:")
    skipped_only = [
        {"week": "2024-01-08", "decision": "NO TRADE", "net_premium": None, "max_loss": None, "outcome": "SKIPPED", "pnl": 0.0},
        {"week": "2024-01-15", "decision": "NO TRADE", "net_premium": None, "max_loss": None, "outcome": "SKIPPED", "pnl": 0.0},
    ]
    skipped_result = evaluate_backtest(skipped_only)
    print(f"    total_trades: {skipped_result['total_trades']}")
    print(f"    expectancy: {skipped_result['expectancy']}")
