"""Macro Event Calendar for Trade Annotation.

This module provides awareness of major macro events for analytical
and journaling purposes. It does NOT affect trade decisions.

Events tracked:
- CPI (Consumer Price Index)
- FOMC (Federal Open Market Committee)
- NFP (Non-Farm Payrolls)
- Quad Witching (quarterly options expiration)

All functions degrade gracefully and never throw exceptions.
"""

from datetime import datetime, timedelta
from typing import Any


MACRO_EVENTS_2024_2026 = {
    "CPI": [
        "2024-01-11", "2024-02-13", "2024-03-12", "2024-04-10", "2024-05-15",
        "2024-06-12", "2024-07-11", "2024-08-14", "2024-09-11", "2024-10-10",
        "2024-11-13", "2024-12-11",
        "2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10", "2025-05-13",
        "2025-06-11", "2025-07-11", "2025-08-12", "2025-09-11", "2025-10-10",
        "2025-11-13", "2025-12-10",
        "2026-01-13", "2026-02-11", "2026-03-11", "2026-04-14", "2026-05-12",
        "2026-06-10", "2026-07-14", "2026-08-12", "2026-09-11", "2026-10-13",
        "2026-11-12", "2026-12-10",
    ],
    "FOMC": [
        "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31",
        "2024-09-18", "2024-11-07", "2024-12-18",
        "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30",
        "2025-09-17", "2025-11-05", "2025-12-17",
        "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29",
        "2026-09-16", "2026-11-04", "2026-12-16",
    ],
    "NFP": [
        "2024-01-05", "2024-02-02", "2024-03-08", "2024-04-05", "2024-05-03",
        "2024-06-07", "2024-07-05", "2024-08-02", "2024-09-06", "2024-10-04",
        "2024-11-01", "2024-12-06",
        "2025-01-10", "2025-02-07", "2025-03-07", "2025-04-04", "2025-05-02",
        "2025-06-06", "2025-07-03", "2025-08-01", "2025-09-05", "2025-10-03",
        "2025-11-07", "2025-12-05",
        "2026-01-09", "2026-02-06", "2026-03-06", "2026-04-03", "2026-05-08",
        "2026-06-05", "2026-07-02", "2026-08-07", "2026-09-04", "2026-10-02",
        "2026-11-06", "2026-12-04",
    ],
    "QUAD_WITCHING": [
        "2024-03-15", "2024-06-21", "2024-09-20", "2024-12-20",
        "2025-03-21", "2025-06-20", "2025-09-19", "2025-12-19",
        "2026-03-20", "2026-06-19", "2026-09-18", "2026-12-18",
    ],
}


def _parse_date(date_input: str | datetime | None) -> datetime | None:
    """Parse a date string or datetime object.

    Args:
        date_input: Date as string (YYYY-MM-DD) or datetime object.

    Returns:
        datetime object or None if parsing fails.
    """
    if date_input is None:
        return None

    try:
        if isinstance(date_input, datetime):
            return date_input
        if isinstance(date_input, str):
            return datetime.strptime(date_input, "%Y-%m-%d")
        return None
    except Exception:
        return None


def _get_week_range(date: datetime) -> tuple[datetime, datetime]:
    """Get the Monday-Friday range for a given date's week.

    Args:
        date: Any date within the week.

    Returns:
        Tuple of (monday, friday) datetime objects.
    """
    weekday = date.weekday()
    monday = date - timedelta(days=weekday)
    friday = monday + timedelta(days=4)
    return monday, friday


def _is_date_in_week(
    event_date_str: str,
    week_start: datetime,
    week_end: datetime,
) -> bool:
    """Check if an event date falls within a week range.

    Args:
        event_date_str: Event date as YYYY-MM-DD string.
        week_start: Start of week (Monday).
        week_end: End of week (Friday).

    Returns:
        True if event is within the week.
    """
    try:
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
        return week_start <= event_date <= week_end
    except Exception:
        return False


def get_macro_event_tags(date: str | datetime | None) -> list[str]:
    """Get macro event tags for the week containing the given date.

    This function checks if major macro events (CPI, FOMC, NFP, Quad Witching)
    fall within the same trading week as the provided date.

    Args:
        date: Reference date (typically Monday of trade week).
              Can be string "YYYY-MM-DD" or datetime object.

    Returns:
        List of event tags (e.g., ["CPI", "FOMC"]).
        Empty list if no events or if date parsing fails.
    """
    tags: list[str] = []

    try:
        parsed_date = _parse_date(date)
        if parsed_date is None:
            return tags

        week_start, week_end = _get_week_range(parsed_date)

        for event_name, event_dates in MACRO_EVENTS_2024_2026.items():
            for event_date_str in event_dates:
                if _is_date_in_week(event_date_str, week_start, week_end):
                    display_name = event_name.replace("_", " ")
                    if display_name not in tags:
                        tags.append(display_name)
                    break

        return tags

    except Exception:
        return []


def get_event_details(date: str | datetime | None) -> dict[str, Any]:
    """Get detailed event information for the week.

    Args:
        date: Reference date for the week.

    Returns:
        Dictionary with event details and metadata.
    """
    result: dict[str, Any] = {
        "tags": [],
        "has_events": False,
        "week_start": None,
        "week_end": None,
        "detail": "",
        "valid": False,
    }

    try:
        parsed_date = _parse_date(date)
        if parsed_date is None:
            result["detail"] = "Invalid date provided."
            return result

        week_start, week_end = _get_week_range(parsed_date)
        result["week_start"] = week_start.strftime("%Y-%m-%d")
        result["week_end"] = week_end.strftime("%Y-%m-%d")

        tags = get_macro_event_tags(date)
        result["tags"] = tags
        result["has_events"] = len(tags) > 0
        result["valid"] = True

        if tags:
            result["detail"] = f"Macro events this week: {', '.join(tags)}. Volatility may be elevated."
        else:
            result["detail"] = "No major macro events this week."

        return result

    except Exception:
        result["detail"] = "Error checking event calendar."
        return result


if __name__ == "__main__":
    print("=== Macro Event Calendar Test ===\n")

    test_dates = [
        "2024-12-16",
        "2025-01-13",
        "2025-03-17",
        "2025-06-16",
        "2025-09-15",
        "2025-12-15",
        "2024-08-05",
    ]

    for date_str in test_dates:
        tags = get_macro_event_tags(date_str)
        details = get_event_details(date_str)

        print(f"Date: {date_str}")
        print(f"  Week: {details['week_start']} to {details['week_end']}")
        print(f"  Tags: {tags if tags else 'None'}")
        print(f"  Detail: {details['detail']}")
        print()

    print("=== Edge Cases ===")
    print(f"None date: {get_macro_event_tags(None)}")
    print(f"Invalid date: {get_macro_event_tags('not-a-date')}")
    print(f"Empty string: {get_macro_event_tags('')}")
