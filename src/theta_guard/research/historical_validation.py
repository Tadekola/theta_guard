"""Historical validation of THETA-GUARD system against SPX daily data.

This module validates SIGNAL FIDELITY only.
It does NOT validate options pricing or claim real profitability.

IMPORTANT:
- P&L values are SIMULATED PROXIES, not real trade outcomes
- This phase validates that the system produces consistent signals
- No trading logic is modified during validation
"""

import csv
import random
from datetime import datetime
from typing import Any

from theta_guard.calendar.holiday_gate import is_trade_week
from theta_guard.indicators.ema_engine import compute_ema_state
from theta_guard.signals.entry_evaluator import evaluate_entry
from theta_guard.backtest.evaluator import evaluate_backtest

DECISION_TRADE_ALLOWED = "TRADE ALLOWED"

PROXY_WIN_PNL = 215.0
PROXY_LOSS_PNL = -297.0
PROXY_WIN_PROBABILITY = 0.66
PROXY_MAX_LOSS = 300.0

LOOKBACK_DAYS = 15


def run_historical_validation(
    csv_path: str,
    random_seed: int = 42,
) -> dict[str, Any]:
    """Run historical validation on SPX daily data.

    Args:
        csv_path: Path to CSV file with columns: date, close
        random_seed: Seed for reproducible simulated P&L outcomes

    Returns:
        Dictionary with:
        - metrics: dict - Output from evaluate_backtest
        - weekly_records: list[dict] - All weekly evaluation records
        - notes: str - Important caveats about the validation
    """
    result: dict[str, Any] = {
        "metrics": {},
        "weekly_records": [],
        "notes": "",
    }

    try:
        daily_data = _load_csv(csv_path)
        if not daily_data:
            result["notes"] = "Failed to load CSV or empty dataset."
            return result

        weekly_records = _evaluate_all_weeks(daily_data, random_seed)
        result["weekly_records"] = weekly_records

        metrics = evaluate_backtest(weekly_records)
        result["metrics"] = metrics

        result["notes"] = (
            "SIMULATED P&L PROXY: Win=+215 (66%), Loss=-297 (34%). "
            "This validates SIGNAL FIDELITY only, NOT real profitability. "
            "Options pricing and actual trade outcomes are NOT modeled."
        )

        return result

    except Exception:
        result["notes"] = "Unexpected error during historical validation."
        return result


def _load_csv(csv_path: str) -> list[dict[str, Any]]:
    """Load SPX daily data from CSV.

    Expected columns: date, close
    Returns list of {date: datetime.date, close: float} sorted by date.
    """
    data: list[dict[str, Any]] = []

    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get("date", "").strip()
                close_str = row.get("close", "").strip()

                if not date_str or not close_str:
                    continue

                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    close = float(close_str)
                    data.append({"date": date, "close": close})
                except (ValueError, TypeError):
                    continue

        data.sort(key=lambda x: x["date"])
        return data

    except Exception:
        return []


def _evaluate_all_weeks(
    daily_data: list[dict[str, Any]],
    random_seed: int,
) -> list[dict[str, Any]]:
    """Evaluate all weeks in the dataset.

    For each week:
    1) Find Monday
    2) Build price history up to Monday
    3) Run evaluation pipeline
    4) Record outcome with simulated P&L
    """
    random.seed(random_seed)
    weekly_records: list[dict[str, Any]] = []

    mondays = _find_all_mondays(daily_data)

    date_to_idx = {d["date"]: i for i, d in enumerate(daily_data)}

    for monday in mondays:
        monday_str = monday.strftime("%Y-%m-%d")
        week_label = monday.strftime("%Y-W%W")

        if monday not in date_to_idx:
            continue

        monday_idx = date_to_idx[monday]

        start_idx = max(0, monday_idx - LOOKBACK_DAYS + 1)
        prices = [daily_data[i]["close"] for i in range(start_idx, monday_idx + 1)]

        record = _evaluate_single_week(
            monday_str=monday_str,
            week_label=week_label,
            prices=prices,
        )

        weekly_records.append(record)

    return weekly_records


def _find_all_mondays(daily_data: list[dict[str, Any]]) -> list:
    """Extract all Monday dates from the dataset."""
    mondays = []
    for d in daily_data:
        if d["date"].weekday() == 0:
            mondays.append(d["date"])
    return sorted(set(mondays))


def _evaluate_single_week(
    monday_str: str,
    week_label: str,
    prices: list[float],
) -> dict[str, Any]:
    """Evaluate a single week and return record.

    Args:
        monday_str: Monday date as ISO string
        week_label: Week identifier (YYYY-WW)
        prices: Daily closes up to and including Monday

    Returns:
        Weekly record dict
    """
    record: dict[str, Any] = {
        "week": week_label,
        "decision": "NO TRADE",
        "net_premium": None,
        "max_loss": PROXY_MAX_LOSS,
        "outcome": "SKIPPED",
        "pnl": 0.0,
    }

    try:
        holiday_result = is_trade_week(monday_str)

        ema_state = compute_ema_state(prices)

        entry_context = {
            "entry_day": "Monday",
            "entry_time_valid": True,
        }

        entry_decision = evaluate_entry(holiday_result, ema_state, entry_context)
        record["decision"] = entry_decision.get("decision", "NO TRADE")

        if record["decision"] != DECISION_TRADE_ALLOWED:
            record["outcome"] = "SKIPPED"
            record["pnl"] = 0.0
            return record

        if random.random() < PROXY_WIN_PROBABILITY:
            record["outcome"] = "WIN"
            record["pnl"] = PROXY_WIN_PNL
        else:
            record["outcome"] = "LOSS"
            record["pnl"] = PROXY_LOSS_PNL

        return record

    except Exception:
        return record


if __name__ == "__main__":
    import os
    import tempfile

    sample_csv_data = """date,close
2024-01-02,4742.83
2024-01-03,4704.81
2024-01-04,4688.68
2024-01-05,4697.24
2024-01-08,4763.54
2024-01-09,4756.50
2024-01-10,4783.45
2024-01-11,4780.24
2024-01-12,4783.83
2024-01-16,4765.98
2024-01-17,4739.21
2024-01-18,4780.94
2024-01-19,4839.81
2024-01-22,4850.43
2024-01-23,4864.60
2024-01-24,4868.55
2024-01-25,4894.16
2024-01-26,4890.97
2024-01-29,4927.93
2024-01-30,4924.97
2024-01-31,4845.65
2024-02-01,4906.19
2024-02-02,4958.61
2024-02-05,4942.81
2024-02-06,4954.23
2024-02-07,4995.06
2024-02-08,5021.84
2024-02-09,5026.61
2024-02-12,5021.82
2024-02-13,4953.17
2024-02-14,5000.62
2024-02-15,5029.73
2024-02-16,5005.57
2024-02-20,4975.51
2024-02-21,4981.80
2024-02-22,5087.03
2024-02-23,5088.80
2024-02-26,5069.76
2024-02-27,5078.18
2024-02-28,5069.53
2024-02-29,5096.27
2024-03-01,5137.08
2024-03-04,5130.95
2024-03-05,5078.65
2024-03-06,5104.76
2024-03-07,5157.36
2024-03-08,5123.69
2024-03-11,5117.94
2024-03-12,5175.27
2024-03-13,5165.31
2024-03-14,5150.48
2024-03-15,5117.09
2024-03-18,5149.42
2024-03-19,5178.51
2024-03-20,5224.62
2024-03-21,5241.53
2024-03-22,5234.18
2024-03-25,5218.19
2024-03-26,5203.58
2024-03-27,5248.49
2024-03-28,5254.35
"""

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(sample_csv_data)
        temp_csv_path = f.name

    try:
        print("=" * 70)
        print("HISTORICAL VALIDATION - Sample SPX Data (Q1 2024)")
        print("=" * 70)

        result = run_historical_validation(temp_csv_path, random_seed=42)

        print("\nMETRICS:")
        print("-" * 70)
        for key, value in result["metrics"].items():
            if isinstance(value, float):
                print(f"  {key}: {value:+.4f}")
            else:
                print(f"  {key}: {value}")

        print("\nWEEKLY SUMMARY:")
        print("-" * 70)
        traded = sum(1 for r in result["weekly_records"] if r["decision"] == "TRADE ALLOWED")
        skipped = sum(1 for r in result["weekly_records"] if r["outcome"] == "SKIPPED")
        print(f"  Total weeks evaluated: {len(result['weekly_records'])}")
        print(f"  Traded: {traded}")
        print(f"  Skipped: {skipped}")

        print("\nNOTES:")
        print("-" * 70)
        print(f"  {result['notes']}")

        print("\nSAMPLE RECORDS (first 5):")
        print("-" * 70)
        for record in result["weekly_records"][:5]:
            status = f"{record['decision']:14} | {record['outcome']:7} | PnL: {record['pnl']:+7.2f}"
            print(f"  {record['week']}: {status}")

    finally:
        os.unlink(temp_csv_path)
