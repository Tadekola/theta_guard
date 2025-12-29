"""Holiday gate for filtering trading days based on market holidays.

This module enforces HARD BLOCK rules from the Trading Charter:
- Section 3.1: Monday is a U.S. market holiday -> NO TRADE
- Section 3.2: Friday is a U.S. market holiday -> NO TRADE
- Section 6.3: Holiday calendars must be authoritative
- Section 6.4: If data ambiguity exists, default to NO TRADE
"""

from datetime import datetime, timedelta
from typing import Any

import pandas_market_calendars as mcal


def is_trade_week(monday_date: str) -> dict[str, Any]:
    """Determine if a trade week is allowed based on holiday rules.

    Evaluates whether the given Monday and its corresponding Friday
    are both valid trading days according to the NYSE calendar.

    Args:
        monday_date: ISO format date string (YYYY-MM-DD) representing
                     the Monday of the trade week to evaluate.

    Returns:
        Dictionary with exactly these keys:
        - is_trade_week: bool - True only if both Monday and Friday are trading days
        - monday_trading_day: bool - True if Monday is a trading day
        - friday_trading_day: bool - True if Friday is a trading day
        - reason: str - Human-readable explanation of the result
    """
    result = {
        "is_trade_week": False,
        "monday_trading_day": False,
        "friday_trading_day": False,
        "reason": "",
    }

    try:
        monday = datetime.strptime(monday_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        result["reason"] = f"Invalid date format: {monday_date}. Expected YYYY-MM-DD."
        return result

    if monday.weekday() != 0:
        result["reason"] = f"Date {monday_date} is not a Monday."
        return result

    friday = monday + timedelta(days=4)

    try:
        nyse = mcal.get_calendar("NYSE")
    except Exception:
        result["reason"] = "Failed to load NYSE calendar. Defaulting to NO TRADE."
        return result

    try:
        schedule = nyse.schedule(start_date=monday, end_date=friday)
    except Exception:
        result["reason"] = "Failed to retrieve market schedule. Defaulting to NO TRADE."
        return result

    if schedule is None or schedule.empty:
        result["reason"] = "No trading days found in the specified week."
        return result

    trading_dates = set(schedule.index.date)

    monday_is_trading_day = monday in trading_dates
    friday_is_trading_day = friday in trading_dates

    result["monday_trading_day"] = monday_is_trading_day
    result["friday_trading_day"] = friday_is_trading_day

    if not monday_is_trading_day and not friday_is_trading_day:
        result["reason"] = (
            f"HARD BLOCK: Both Monday ({monday_date}) and Friday ({friday}) "
            "are market holidays."
        )
    elif not monday_is_trading_day:
        result["reason"] = f"HARD BLOCK: Monday ({monday_date}) is a market holiday."
    elif not friday_is_trading_day:
        result["reason"] = f"HARD BLOCK: Friday ({friday}) is a market holiday."
    else:
        result["is_trade_week"] = True
        result["reason"] = (
            f"Trade week allowed: Monday ({monday_date}) and Friday ({friday}) "
            "are both trading days."
        )

    return result


if __name__ == "__main__":
    test_cases = [
        ("2024-01-08", "Normal full trading week"),
        ("2024-01-15", "Monday is MLK Day (holiday)"),
        ("2024-03-25", "Friday is Good Friday (holiday)"),
        ("2024-07-01", "Week before July 4th (Thursday holiday, Friday open)"),
        ("2024-12-23", "Christmas week (Wednesday holiday)"),
    ]

    for date, description in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {description}")
        print(f"Monday: {date}")
        print("-" * 60)
        result = is_trade_week(date)
        for key, value in result.items():
            print(f"  {key}: {value}")
