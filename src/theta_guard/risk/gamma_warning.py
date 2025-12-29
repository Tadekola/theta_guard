"""Gamma / Danger Zone warning calculator.

This module computes a proxy warning level based on distance from
spot to short strike relative to expected move.

IMPORTANT: This is READ-ONLY advisory information.
It does NOT affect the core TRADE ALLOWED / NO TRADE decision.
This is NOT full GEX analysis - it's a simplified proximity warning.

Charter compliance:
- Advisory layer only - no decision override
- Graceful degradation on missing data
- Clear labeling of data sources
"""

from typing import Any
import math


def compute_gamma_warning(
    spot: float | None,
    short_strike: float | None,
    expected_move: float | None = None,
    iv: float | None = None,
    dte: int | None = None,
) -> dict[str, Any]:
    """Compute gamma/danger zone warning level.

    Args:
        spot: Current SPX spot price (or proxy).
        short_strike: Strike price of the short leg (2x quantity).
        expected_move: Pre-computed expected move, if available.
        iv: Implied volatility (decimal, e.g., 0.15 for 15%), if available.
        dte: Days to expiration, if available.

    Returns:
        Dictionary with:
        - level: "NORMAL"|"ELEVATED"|"HIGH"|"N/A"
        - detail: str explanation
        - distance: float|None
        - expected_move: float|None
        - move_source: str|None ("iv_based" or "fallback")
        - valid: bool
    """
    result: dict[str, Any] = {
        "level": "N/A",
        "detail": "",
        "distance": None,
        "expected_move": None,
        "move_source": None,
        "valid": False,
    }

    try:
        if spot is None or spot <= 0:
            result["detail"] = "Spot price missing or invalid."
            return result

        if short_strike is None or short_strike <= 0:
            result["detail"] = "Short strike missing or invalid."
            return result

        distance = abs(spot - short_strike)
        result["distance"] = round(distance, 2)

        exp_move, move_source = _compute_expected_move(
            spot, expected_move, iv, dte
        )

        if exp_move is None or exp_move <= 0:
            result["detail"] = "Expected move could not be computed."
            return result

        result["expected_move"] = round(exp_move, 2)
        result["move_source"] = move_source

        level, detail = _determine_level(distance, exp_move, spot, short_strike)

        result["level"] = level
        result["detail"] = detail
        result["valid"] = True

        return result

    except Exception:
        result["detail"] = "Unexpected error computing gamma warning."
        return result


def _compute_expected_move(
    spot: float,
    expected_move: float | None,
    iv: float | None,
    dte: int | None,
) -> tuple[float | None, str | None]:
    """Compute expected move from IV or use fallback.

    Returns:
        Tuple of (expected_move, source_label)
    """
    if expected_move is not None and expected_move > 0:
        return expected_move, "provided"

    if iv is not None and iv > 0 and dte is not None and dte > 0:
        time_factor = math.sqrt(dte / 365.0)
        exp_move = spot * iv * time_factor
        return exp_move, "iv_based"

    fallback = spot * 0.015
    return fallback, "fallback_1.5pct"


def _determine_level(
    distance: float,
    expected_move: float,
    spot: float,
    short_strike: float,
) -> tuple[str, str]:
    """Determine warning level based on distance vs expected move."""
    direction = "below" if short_strike < spot else "above"

    if distance < 0.5 * expected_move:
        level = "HIGH"
        detail = (
            f"⚠️ HIGH RISK: Short strike {short_strike:.0f} is only {distance:.1f} pts "
            f"{direction} spot ({spot:.0f}). This is < 0.5x expected move ({expected_move:.1f})."
        )
    elif distance < expected_move:
        level = "ELEVATED"
        detail = (
            f"⚡ ELEVATED: Short strike {short_strike:.0f} is {distance:.1f} pts "
            f"{direction} spot ({spot:.0f}). This is < 1x expected move ({expected_move:.1f})."
        )
    else:
        level = "NORMAL"
        detail = (
            f"✓ NORMAL: Short strike {short_strike:.0f} is {distance:.1f} pts "
            f"{direction} spot ({spot:.0f}). This is >= 1x expected move ({expected_move:.1f})."
        )

    return level, detail


def extract_short_strike(bwb_structure: dict[str, Any] | None) -> float | None:
    """Extract the short strike from BWB structure (SELL with quantity 2)."""
    if not isinstance(bwb_structure, dict):
        return None

    legs = bwb_structure.get("legs", [])
    for leg in legs:
        if leg.get("action") == "SELL" and leg.get("quantity") == 2:
            return leg.get("strike")
    return None


if __name__ == "__main__":
    print("=" * 70)
    print("TEST 1: Normal distance - safe position")
    print("-" * 70)
    result = compute_gamma_warning(
        spot=5950.0,
        short_strike=5875.0,
        expected_move=60.0,
    )
    print(f"  level: {result['level']}")
    print(f"  distance: {result['distance']}")
    print(f"  expected_move: {result['expected_move']}")
    print(f"  move_source: {result['move_source']}")
    print(f"  detail: {result['detail']}")

    print("\n" + "=" * 70)
    print("TEST 2: Elevated risk - within 1x expected move")
    print("-" * 70)
    result = compute_gamma_warning(
        spot=5920.0,
        short_strike=5875.0,
        expected_move=60.0,
    )
    print(f"  level: {result['level']}")
    print(f"  distance: {result['distance']}")
    print(f"  detail: {result['detail']}")

    print("\n" + "=" * 70)
    print("TEST 3: High risk - within 0.5x expected move")
    print("-" * 70)
    result = compute_gamma_warning(
        spot=5890.0,
        short_strike=5875.0,
        expected_move=60.0,
    )
    print(f"  level: {result['level']}")
    print(f"  distance: {result['distance']}")
    print(f"  detail: {result['detail']}")

    print("\n" + "=" * 70)
    print("TEST 4: IV-based expected move calculation")
    print("-" * 70)
    result = compute_gamma_warning(
        spot=5950.0,
        short_strike=5875.0,
        iv=0.15,
        dte=4,
    )
    print(f"  level: {result['level']}")
    print(f"  expected_move: {result['expected_move']}")
    print(f"  move_source: {result['move_source']}")
    print(f"  detail: {result['detail']}")

    print("\n" + "=" * 70)
    print("TEST 5: Fallback expected move (no IV)")
    print("-" * 70)
    result = compute_gamma_warning(
        spot=5950.0,
        short_strike=5875.0,
    )
    print(f"  level: {result['level']}")
    print(f"  expected_move: {result['expected_move']}")
    print(f"  move_source: {result['move_source']}")
    print(f"  detail: {result['detail']}")

    print("\n" + "=" * 70)
    print("TEST 6: Missing spot")
    print("-" * 70)
    result = compute_gamma_warning(
        spot=None,
        short_strike=5875.0,
    )
    print(f"  level: {result['level']}")
    print(f"  valid: {result['valid']}")
    print(f"  detail: {result['detail']}")
