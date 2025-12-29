"""EMA engine for exponential moving average calculations.

This module provides pure EMA computation functions.
It does NOT make trading decisions — it only reports indicator state.

Charter compliance:
- Section 4.1: 3-period EMA above 8-period EMA (computed here, evaluated elsewhere)
- Section 4.3: Slope of 8-period EMA not negative (computed here, evaluated elsewhere)
- Section 6.1: All indicators must be calculated deterministically
"""

from typing import Any

SLOPE_EPSILON = 1e-9


def compute_ema_series(prices: list[float], period: int) -> list[float] | None:
    """Compute an EMA series for all price points.

    Args:
        prices: List of prices ordered oldest to newest.
        period: The EMA period (e.g., 3 or 8).

    Returns:
        List of EMA values (same length as prices), or None if insufficient data.
        Each EMA[i] corresponds to prices[i].

    Formula:
        multiplier = 2 / (period + 1)
        EMA_today = (Price_today - EMA_yesterday) * multiplier + EMA_yesterday
        First EMA is seeded with SMA of first `period` prices.
    """
    try:
        if not isinstance(prices, list):
            return None
        if not isinstance(period, int) or period < 1:
            return None
        if len(prices) < period + 2:
            return None
        if not all(isinstance(p, (int, float)) for p in prices):
            return None

        multiplier = 2.0 / (period + 1)
        ema_series: list[float] = []

        sma_seed = sum(prices[:period]) / period
        for i in range(period):
            ema_series.append(sma_seed)

        ema_previous = sma_seed
        for i in range(period, len(prices)):
            ema_current = (prices[i] - ema_previous) * multiplier + ema_previous
            ema_series.append(ema_current)
            ema_previous = ema_current

        return ema_series

    except Exception:
        return None


def compute_ema_state(
    prices: list[float],
    short_period: int = 3,
    long_period: int = 8,
) -> dict[str, Any]:
    """Compute EMA state for signal evaluation.

    Args:
        prices: List of prices ordered oldest to newest.
        short_period: Period for the short EMA (default 3).
        long_period: Period for the long EMA (default 8).

    Returns:
        Dictionary with exactly these keys:
        - short_ema: float | None - Most recent short EMA value
        - long_ema: float | None - Most recent long EMA value
        - short_above_long: bool - True if short EMA > long EMA
        - long_ema_slope: str - "positive", "zero", or "negative"
        - data_points_used: int - Number of price points provided
        - valid: bool - True if computation succeeded with sufficient data
        - reason: str - Human-readable explanation
    """
    result: dict[str, Any] = {
        "short_ema": None,
        "long_ema": None,
        "short_above_long": False,
        "long_ema_slope": "negative",
        "data_points_used": 0,
        "valid": False,
        "reason": "",
    }

    try:
        if not isinstance(prices, list):
            result["reason"] = "Invalid input: prices must be a list."
            return result

        result["data_points_used"] = len(prices)

        if not isinstance(short_period, int) or short_period < 1:
            result["reason"] = f"Invalid short_period: {short_period}. Must be positive integer."
            return result

        if not isinstance(long_period, int) or long_period < 1:
            result["reason"] = f"Invalid long_period: {long_period}. Must be positive integer."
            return result

        if short_period >= long_period:
            result["reason"] = (
                f"short_period ({short_period}) must be less than long_period ({long_period})."
            )
            return result

        min_required = long_period + 2
        if len(prices) < min_required:
            result["reason"] = (
                f"Insufficient data: {len(prices)} prices provided, "
                f"minimum {min_required} required for period {long_period}."
            )
            return result

        short_ema_series = compute_ema_series(prices, short_period)
        long_ema_series = compute_ema_series(prices, long_period)

        if short_ema_series is None:
            result["reason"] = "Failed to compute short EMA series."
            return result

        if long_ema_series is None:
            result["reason"] = "Failed to compute long EMA series."
            return result

        short_ema_current = short_ema_series[-1]
        long_ema_current = long_ema_series[-1]
        long_ema_previous = long_ema_series[-2]

        result["short_ema"] = short_ema_current
        result["long_ema"] = long_ema_current

        result["short_above_long"] = short_ema_current > long_ema_current

        slope_diff = long_ema_current - long_ema_previous
        if slope_diff > SLOPE_EPSILON:
            result["long_ema_slope"] = "positive"
        elif slope_diff < -SLOPE_EPSILON:
            result["long_ema_slope"] = "negative"
        else:
            result["long_ema_slope"] = "zero"

        result["valid"] = True
        result["reason"] = (
            f"EMA state computed: short({short_period})={short_ema_current:.4f}, "
            f"long({long_period})={long_ema_current:.4f}, "
            f"short_above_long={result['short_above_long']}, "
            f"slope={result['long_ema_slope']}."
        )

        return result

    except Exception:
        result["reason"] = "Unexpected error during EMA computation. Defaulting to invalid state."
        return result


if __name__ == "__main__":
    print("=" * 70)
    print("TEST 1: Rising price series")
    print("-" * 70)
    rising_prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0]
    result = compute_ema_state(rising_prices)
    for key, value in result.items():
        print(f"  {key}: {value}")
    print(f"  Expected: short_above_long=True, long_ema_slope=positive, valid=True")

    print("\n" + "=" * 70)
    print("TEST 2: Falling price series")
    print("-" * 70)
    falling_prices = [110.0, 109.0, 108.0, 107.0, 106.0, 105.0, 104.0, 103.0, 102.0, 101.0, 100.0]
    result = compute_ema_state(falling_prices)
    for key, value in result.items():
        print(f"  {key}: {value}")
    print(f"  Expected: short_above_long=False, long_ema_slope=negative, valid=True")

    print("\n" + "=" * 70)
    print("TEST 3: Insufficient data")
    print("-" * 70)
    insufficient_prices = [100.0, 101.0, 102.0, 103.0, 104.0]
    result = compute_ema_state(insufficient_prices)
    for key, value in result.items():
        print(f"  {key}: {value}")
    print(f"  Expected: valid=False, reason explains insufficient data")

    print("\n" + "=" * 70)
    print("TEST 4: Flat price series (slope should be zero or near-zero)")
    print("-" * 70)
    flat_prices = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
    result = compute_ema_state(flat_prices)
    for key, value in result.items():
        print(f"  {key}: {value}")
    print(f"  Expected: long_ema_slope=zero, valid=True")
