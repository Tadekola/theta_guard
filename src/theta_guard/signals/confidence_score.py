"""Signal confidence score calculator.

This module computes an advisory confidence score (0-10) based on
EMA state, BWB structure quality, and market positioning.

IMPORTANT: This is READ-ONLY advisory information.
It does NOT affect the core TRADE ALLOWED / NO TRADE decision.

Charter compliance:
- Advisory layer only - no decision override
- Graceful degradation on missing data
- Deterministic scoring rules
"""

from typing import Any


def compute_confidence_score(
    ema_state: dict[str, Any],
    bwb_structure: dict[str, Any],
    spot: float | None,
    expected_move: float | None = None,
) -> dict[str, Any]:
    """Compute a confidence score for the trade setup.

    Args:
        ema_state: Output from compute_ema_state.
            Expected keys: valid, short_above_long, long_ema_slope,
                          short_ema, long_ema
        bwb_structure: Output from build_bwb_structure.
            Expected keys: valid, legs, net_premium, max_loss
        spot: Current SPX spot price (or proxy from latest close).
        expected_move: Expected price move until expiration.
            If None, uses fallback of spot * 0.015.

    Returns:
        Dictionary with:
        - score: float (0 to 10)
        - grade: "A"|"B"|"C"|"D"|"N/A"
        - valid: bool
        - reasons: list[str]
    """
    result: dict[str, Any] = {
        "score": 0.0,
        "grade": "N/A",
        "valid": False,
        "reasons": [],
    }

    try:
        if not _validate_inputs(ema_state, bwb_structure, spot, result):
            return result

        score = 5.0
        reasons: list[str] = []

        score, reasons = _score_ema_separation(
            ema_state, spot, score, reasons
        )

        score, reasons = _score_ema_slope(ema_state, score, reasons)

        score, reasons = _score_credit_to_risk(bwb_structure, score, reasons)

        score, reasons = _score_distance_to_short(
            bwb_structure, spot, expected_move, score, reasons
        )

        score = max(0.0, min(10.0, score))

        grade = _compute_grade(score)

        result["score"] = round(score, 1)
        result["grade"] = grade
        result["valid"] = True
        result["reasons"] = reasons

        return result

    except Exception:
        result["reasons"].append("Unexpected error computing confidence score.")
        return result


def _validate_inputs(
    ema_state: dict[str, Any],
    bwb_structure: dict[str, Any],
    spot: float | None,
    result: dict[str, Any],
) -> bool:
    """Validate inputs and populate result with failure reasons if invalid."""
    if not isinstance(ema_state, dict) or not ema_state.get("valid", False):
        result["reasons"].append("EMA state is invalid or missing.")
        return False

    if not isinstance(bwb_structure, dict) or not bwb_structure.get("valid", False):
        result["reasons"].append("BWB structure is invalid or missing.")
        return False

    if spot is None or spot <= 0:
        result["reasons"].append("Spot price is missing or invalid.")
        return False

    return True


def _score_ema_separation(
    ema_state: dict[str, Any],
    spot: float,
    score: float,
    reasons: list[str],
) -> tuple[float, list[str]]:
    """Score based on EMA separation magnitude (+0 to +2)."""
    short_ema = ema_state.get("short_ema")
    long_ema = ema_state.get("long_ema")

    if short_ema is None or long_ema is None:
        reasons.append("EMA values missing - no separation bonus.")
        return score, reasons

    separation = abs(short_ema - long_ema)
    normalization = spot * 0.002

    if normalization <= 0:
        reasons.append("Invalid normalization for EMA separation.")
        return score, reasons

    separation_ratio = separation / normalization
    bonus = min(2.0, separation_ratio)
    score += bonus

    if bonus >= 1.5:
        reasons.append(f"Strong EMA separation (+{bonus:.1f}): {separation:.2f} pts")
    elif bonus >= 0.5:
        reasons.append(f"Moderate EMA separation (+{bonus:.1f}): {separation:.2f} pts")
    else:
        reasons.append(f"Weak EMA separation (+{bonus:.1f}): {separation:.2f} pts")

    return score, reasons


def _score_ema_slope(
    ema_state: dict[str, Any],
    score: float,
    reasons: list[str],
) -> tuple[float, list[str]]:
    """Score based on long EMA slope (+1, -0.5, or 0)."""
    slope = ema_state.get("long_ema_slope", "unknown")

    if slope == "positive":
        score += 1.0
        reasons.append("Long EMA slope positive (+1.0)")
    elif slope == "zero":
        score -= 0.5
        reasons.append("Long EMA slope flat (-0.5)")
    elif slope == "negative":
        reasons.append("Long EMA slope negative (already blocked by signal gate)")

    return score, reasons


def _score_credit_to_risk(
    bwb_structure: dict[str, Any],
    score: float,
    reasons: list[str],
) -> tuple[float, list[str]]:
    """Score based on credit-to-risk ratio (+1, 0, or -1)."""
    net_premium = bwb_structure.get("net_premium", 0)
    max_loss = bwb_structure.get("max_loss", 0)

    if max_loss is None or max_loss <= 0:
        reasons.append("Max loss unknown - cannot compute credit/risk ratio.")
        return score, reasons

    credit_to_risk = net_premium / max_loss if max_loss > 0 else 0

    if credit_to_risk >= 0.5:
        score += 1.0
        reasons.append(f"Good credit/risk ratio (+1.0): {credit_to_risk:.2f}")
    elif credit_to_risk >= 0.3:
        reasons.append(f"Acceptable credit/risk ratio: {credit_to_risk:.2f}")
    else:
        score -= 1.0
        reasons.append(f"Poor credit/risk ratio (-1.0): {credit_to_risk:.2f}")

    return score, reasons


def _score_distance_to_short(
    bwb_structure: dict[str, Any],
    spot: float,
    expected_move: float | None,
    score: float,
    reasons: list[str],
) -> tuple[float, list[str]]:
    """Score based on distance from spot to short strike (+1, 0, or -1)."""
    legs = bwb_structure.get("legs", [])
    short_strike = None

    for leg in legs:
        if leg.get("action") == "SELL" and leg.get("quantity") == 2:
            short_strike = leg.get("strike")
            break

    if short_strike is None:
        reasons.append("Short strike not found in structure.")
        return score, reasons

    if expected_move is None or expected_move <= 0:
        expected_move = spot * 0.015
        move_source = "fallback 1.5%"
    else:
        move_source = "IV-based"

    distance = abs(spot - short_strike)

    if distance >= expected_move:
        score += 1.0
        reasons.append(
            f"Good distance to short (+1.0): {distance:.1f} >= {expected_move:.1f} ({move_source})"
        )
    elif distance >= 0.5 * expected_move:
        reasons.append(
            f"Moderate distance to short: {distance:.1f} vs {expected_move:.1f} ({move_source})"
        )
    else:
        score -= 1.0
        reasons.append(
            f"Short strike too close (-1.0): {distance:.1f} < {0.5*expected_move:.1f} ({move_source})"
        )

    return score, reasons


def _compute_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 8.0:
        return "A"
    elif score >= 6.5:
        return "B"
    elif score >= 5.0:
        return "C"
    else:
        return "D"


if __name__ == "__main__":
    print("=" * 70)
    print("TEST 1: Valid inputs - good setup")
    print("-" * 70)
    result = compute_confidence_score(
        ema_state={
            "valid": True,
            "short_above_long": True,
            "long_ema_slope": "positive",
            "short_ema": 5920.0,
            "long_ema": 5900.0,
        },
        bwb_structure={
            "valid": True,
            "legs": [
                {"action": "SELL", "quantity": 2, "strike": 5875.0},
                {"action": "BUY", "quantity": 1, "strike": 5900.0},
                {"action": "BUY", "quantity": 1, "strike": 5825.0},
            ],
            "net_premium": 2.50,
            "max_loss": 4.00,
        },
        spot=5950.0,
        expected_move=60.0,
    )
    print(f"  score: {result['score']}")
    print(f"  grade: {result['grade']}")
    print(f"  valid: {result['valid']}")
    print("  reasons:")
    for r in result["reasons"]:
        print(f"    - {r}")

    print("\n" + "=" * 70)
    print("TEST 2: Invalid EMA state")
    print("-" * 70)
    result = compute_confidence_score(
        ema_state={"valid": False},
        bwb_structure={"valid": True, "legs": [], "net_premium": 2.0, "max_loss": 4.0},
        spot=5950.0,
    )
    print(f"  score: {result['score']}")
    print(f"  grade: {result['grade']}")
    print(f"  valid: {result['valid']}")
    print(f"  reasons: {result['reasons']}")

    print("\n" + "=" * 70)
    print("TEST 3: Poor credit/risk ratio")
    print("-" * 70)
    result = compute_confidence_score(
        ema_state={
            "valid": True,
            "short_above_long": True,
            "long_ema_slope": "zero",
            "short_ema": 5905.0,
            "long_ema": 5900.0,
        },
        bwb_structure={
            "valid": True,
            "legs": [{"action": "SELL", "quantity": 2, "strike": 5940.0}],
            "net_premium": 0.50,
            "max_loss": 5.00,
        },
        spot=5950.0,
    )
    print(f"  score: {result['score']}")
    print(f"  grade: {result['grade']}")
    print(f"  valid: {result['valid']}")
    print("  reasons:")
    for r in result["reasons"]:
        print(f"    - {r}")
