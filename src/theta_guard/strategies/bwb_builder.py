"""BWB builder for broken wing butterfly strategy construction.

This module constructs Broken Wing Butterfly (BWB) option structures.
It does NOT decide whether a trade should be entered.

Charter compliance:
- Section 5.1: Only BWB structures permitted
- Section 5.2: Risk must be fully defined at entry
- Section 5.3: Maximum loss must be known and finite
- Section 5.4: Structure must be asymmetric with favorable reward-to-risk
- Section 5.5: No discretionary strike selection outside defined rules
"""

from typing import Any

STRUCTURE_PUT_CREDIT_BWB = "PUT_CREDIT_BWB"
STRUCTURE_CALL_DEBIT_BWB = "CALL_DEBIT_BWB"

TARGET_DELTA_PUT_SHORT = 0.55
TARGET_DELTA_CALL_SHORT = 0.45


def build_bwb_structure(
    option_chain: list[dict[str, Any]],
    structure_type: str,
) -> dict[str, Any]:
    """Build a Broken Wing Butterfly option structure.

    Args:
        option_chain: List of option records for a single expiration.
            Each dict must contain: type, strike, delta, bid, ask
        structure_type: "PUT_CREDIT_BWB" or "CALL_DEBIT_BWB"

    Returns:
        Dictionary with exactly these keys:
        - structure_type: str - The requested structure type
        - legs: list[dict] - List of leg definitions
        - net_premium: float - Net credit (positive) or debit (negative)
        - max_loss: float | None - Maximum possible loss
        - valid: bool - True if structure was built successfully
        - reason: str - Human-readable explanation
    """
    result: dict[str, Any] = {
        "structure_type": structure_type,
        "legs": [],
        "net_premium": 0.0,
        "max_loss": None,
        "valid": False,
        "reason": "",
    }

    try:
        if not isinstance(option_chain, list) or len(option_chain) == 0:
            result["reason"] = "Invalid or empty option chain provided."
            return result

        if structure_type == STRUCTURE_PUT_CREDIT_BWB:
            return _build_put_credit_bwb(option_chain, result)
        elif structure_type == STRUCTURE_CALL_DEBIT_BWB:
            return _build_call_debit_bwb(option_chain, result)
        else:
            result["reason"] = f"Unknown structure type: {structure_type}"
            return result

    except Exception:
        result["reason"] = "Unexpected error during structure construction."
        return result


def _build_put_credit_bwb(
    option_chain: list[dict[str, Any]],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Build a PUT credit BWB structure.

    Structure:
    - Sell 2 puts at ~55 delta (short strike)
    - Buy 1 put one strike ABOVE short strike (long upper)
    - Buy 1 put two strikes BELOW short strike (long lower / wing)
    """
    puts = _filter_options(option_chain, "put")
    if not puts:
        result["reason"] = "No put options found in chain."
        return result

    puts_sorted = sorted(puts, key=lambda x: x["strike"])
    strikes = [p["strike"] for p in puts_sorted]

    short_put = _find_closest_delta(puts_sorted, TARGET_DELTA_PUT_SHORT)
    if short_put is None:
        result["reason"] = "Could not find put option near 55 delta."
        return result

    short_strike = short_put["strike"]
    short_idx = strikes.index(short_strike)

    if short_idx + 1 >= len(strikes):
        result["reason"] = f"No strike available above short strike {short_strike}."
        return result
    long_upper_strike = strikes[short_idx + 1]

    if short_idx - 2 < 0:
        result["reason"] = f"Not enough strikes below short strike {short_strike} for wing."
        return result
    long_lower_strike = strikes[short_idx - 2]

    long_upper = _find_option_by_strike(puts_sorted, long_upper_strike)
    long_lower = _find_option_by_strike(puts_sorted, long_lower_strike)

    if long_upper is None:
        result["reason"] = f"Could not find put at strike {long_upper_strike}."
        return result
    if long_lower is None:
        result["reason"] = f"Could not find put at strike {long_lower_strike}."
        return result

    short_price = _mid_price(short_put)
    long_upper_price = _mid_price(long_upper)
    long_lower_price = _mid_price(long_lower)

    net_premium = (2 * short_price) - long_upper_price - long_lower_price

    upper_spread_width = long_upper_strike - short_strike
    max_loss_upper = upper_spread_width - net_premium

    result["legs"] = [
        _make_leg("SELL", 2, "put", short_strike, short_price, short_put.get("delta")),
        _make_leg("BUY", 1, "put", long_upper_strike, long_upper_price, long_upper.get("delta")),
        _make_leg("BUY", 1, "put", long_lower_strike, long_lower_price, long_lower.get("delta")),
    ]
    result["net_premium"] = round(net_premium, 4)
    result["max_loss"] = round(max_loss_upper, 4) if max_loss_upper > 0 else 0.0
    result["valid"] = True
    result["reason"] = (
        f"PUT credit BWB built: short {short_strike} (x2), "
        f"long {long_upper_strike}, wing {long_lower_strike}. "
        f"Net credit: {net_premium:.2f}, Max loss: {result['max_loss']:.2f}"
    )

    return result


def _build_call_debit_bwb(
    option_chain: list[dict[str, Any]],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Build a CALL debit BWB structure.

    Structure:
    - Sell 2 calls at ~45 delta (short strike)
    - Buy 1 call two strikes ABOVE short strike (long upper / wing)
    - Buy 1 call one strike BELOW short strike (long lower)
    """
    calls = _filter_options(option_chain, "call")
    if not calls:
        result["reason"] = "No call options found in chain."
        return result

    calls_sorted = sorted(calls, key=lambda x: x["strike"])
    strikes = [c["strike"] for c in calls_sorted]

    short_call = _find_closest_delta(calls_sorted, TARGET_DELTA_CALL_SHORT)
    if short_call is None:
        result["reason"] = "Could not find call option near 45 delta."
        return result

    short_strike = short_call["strike"]
    short_idx = strikes.index(short_strike)

    if short_idx + 2 >= len(strikes):
        result["reason"] = f"Not enough strikes above short strike {short_strike} for wing."
        return result
    long_upper_strike = strikes[short_idx + 2]

    if short_idx - 1 < 0:
        result["reason"] = f"No strike available below short strike {short_strike}."
        return result
    long_lower_strike = strikes[short_idx - 1]

    long_upper = _find_option_by_strike(calls_sorted, long_upper_strike)
    long_lower = _find_option_by_strike(calls_sorted, long_lower_strike)

    if long_upper is None:
        result["reason"] = f"Could not find call at strike {long_upper_strike}."
        return result
    if long_lower is None:
        result["reason"] = f"Could not find call at strike {long_lower_strike}."
        return result

    short_price = _mid_price(short_call)
    long_upper_price = _mid_price(long_upper)
    long_lower_price = _mid_price(long_lower)

    net_premium = (2 * short_price) - long_upper_price - long_lower_price

    lower_spread_width = short_strike - long_lower_strike
    max_loss_lower = lower_spread_width - net_premium

    result["legs"] = [
        _make_leg("SELL", 2, "call", short_strike, short_price, short_call.get("delta")),
        _make_leg("BUY", 1, "call", long_upper_strike, long_upper_price, long_upper.get("delta")),
        _make_leg("BUY", 1, "call", long_lower_strike, long_lower_price, long_lower.get("delta")),
    ]
    result["net_premium"] = round(net_premium, 4)
    result["max_loss"] = round(max_loss_lower, 4) if max_loss_lower > 0 else 0.0
    result["valid"] = True
    result["reason"] = (
        f"CALL debit BWB built: short {short_strike} (x2), "
        f"wing {long_upper_strike}, long {long_lower_strike}. "
        f"Net premium: {net_premium:.2f}, Max loss: {result['max_loss']:.2f}"
    )

    return result


def _filter_options(
    option_chain: list[dict[str, Any]],
    option_type: str,
) -> list[dict[str, Any]]:
    """Filter option chain by type (call or put)."""
    return [opt for opt in option_chain if opt.get("type") == option_type]


def _find_closest_delta(
    options: list[dict[str, Any]],
    target_delta: float,
) -> dict[str, Any] | None:
    """Find option with delta closest to target (by absolute distance)."""
    if not options:
        return None

    closest = None
    min_distance = float("inf")

    for opt in options:
        delta = opt.get("delta")
        if delta is None:
            continue
        distance = abs(abs(delta) - target_delta)
        if distance < min_distance:
            min_distance = distance
            closest = opt

    return closest


def _find_option_by_strike(
    options: list[dict[str, Any]],
    strike: float,
) -> dict[str, Any] | None:
    """Find option by exact strike price."""
    for opt in options:
        if opt.get("strike") == strike:
            return opt
    return None


def _mid_price(option: dict[str, Any]) -> float:
    """Calculate mid-price from bid/ask."""
    bid = option.get("bid", 0.0)
    ask = option.get("ask", 0.0)
    return (bid + ask) / 2.0


def _make_leg(
    action: str,
    quantity: int,
    option_type: str,
    strike: float,
    price: float,
    delta: float | None = None,
) -> dict[str, Any]:
    """Create a leg dictionary."""
    return {
        "action": action,
        "quantity": quantity,
        "type": option_type,
        "strike": strike,
        "price": round(price, 4),
        "delta": round(delta, 4) if delta is not None else None,
    }


if __name__ == "__main__":
    sample_put_chain = [
        {"type": "put", "strike": 5800, "delta": -0.70, "bid": 45.00, "ask": 46.00},
        {"type": "put", "strike": 5825, "delta": -0.65, "bid": 38.00, "ask": 39.00},
        {"type": "put", "strike": 5850, "delta": -0.60, "bid": 32.00, "ask": 33.00},
        {"type": "put", "strike": 5875, "delta": -0.55, "bid": 26.00, "ask": 27.00},
        {"type": "put", "strike": 5900, "delta": -0.50, "bid": 21.00, "ask": 22.00},
        {"type": "put", "strike": 5925, "delta": -0.45, "bid": 17.00, "ask": 18.00},
        {"type": "put", "strike": 5950, "delta": -0.40, "bid": 13.00, "ask": 14.00},
    ]

    sample_call_chain = [
        {"type": "call", "strike": 5850, "delta": 0.60, "bid": 55.00, "ask": 56.00},
        {"type": "call", "strike": 5875, "delta": 0.55, "bid": 45.00, "ask": 46.00},
        {"type": "call", "strike": 5900, "delta": 0.50, "bid": 36.00, "ask": 37.00},
        {"type": "call", "strike": 5925, "delta": 0.45, "bid": 28.00, "ask": 29.00},
        {"type": "call", "strike": 5950, "delta": 0.40, "bid": 21.00, "ask": 22.00},
        {"type": "call", "strike": 5975, "delta": 0.35, "bid": 15.00, "ask": 16.00},
        {"type": "call", "strike": 6000, "delta": 0.30, "bid": 10.00, "ask": 11.00},
    ]

    print("=" * 70)
    print("TEST 1: PUT Credit BWB")
    print("-" * 70)
    result = build_bwb_structure(sample_put_chain, "PUT_CREDIT_BWB")
    print(f"  valid: {result['valid']}")
    print(f"  structure_type: {result['structure_type']}")
    print(f"  net_premium: {result['net_premium']}")
    print(f"  max_loss: {result['max_loss']}")
    print(f"  reason: {result['reason']}")
    print("  legs:")
    for leg in result["legs"]:
        print(f"    {leg['action']} {leg['quantity']}x {leg['type']} @ {leg['strike']} for {leg['price']}")

    print("\n" + "=" * 70)
    print("TEST 2: CALL Debit BWB")
    print("-" * 70)
    result = build_bwb_structure(sample_call_chain, "CALL_DEBIT_BWB")
    print(f"  valid: {result['valid']}")
    print(f"  structure_type: {result['structure_type']}")
    print(f"  net_premium: {result['net_premium']}")
    print(f"  max_loss: {result['max_loss']}")
    print(f"  reason: {result['reason']}")
    print("  legs:")
    for leg in result["legs"]:
        print(f"    {leg['action']} {leg['quantity']}x {leg['type']} @ {leg['strike']} for {leg['price']}")

    print("\n" + "=" * 70)
    print("TEST 3: Missing strike → invalid result")
    print("-" * 70)
    sparse_chain = [
        {"type": "put", "strike": 5875, "delta": -0.55, "bid": 26.00, "ask": 27.00},
        {"type": "put", "strike": 5900, "delta": -0.50, "bid": 21.00, "ask": 22.00},
    ]
    result = build_bwb_structure(sparse_chain, "PUT_CREDIT_BWB")
    print(f"  valid: {result['valid']}")
    print(f"  reason: {result['reason']}")

    print("\n" + "=" * 70)
    print("TEST 4: Empty chain → invalid result")
    print("-" * 70)
    result = build_bwb_structure([], "PUT_CREDIT_BWB")
    print(f"  valid: {result['valid']}")
    print(f"  reason: {result['reason']}")
