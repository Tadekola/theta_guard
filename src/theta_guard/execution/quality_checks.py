"""Execution quality checklist for trade entry.

This module evaluates execution quality factors like spreads,
liquidity, and premium thresholds.

IMPORTANT: This is READ-ONLY advisory information.
It does NOT affect the core TRADE ALLOWED / NO TRADE decision.

Charter compliance:
- Advisory layer only - no decision override
- Graceful degradation on missing data
- No exceptions escape
"""

from typing import Any


def evaluate_execution_quality(
    option_chain: list[dict[str, Any]] | None,
    bwb_structure: dict[str, Any] | None,
) -> dict[str, Any]:
    """Evaluate execution quality for the proposed trade.

    Args:
        option_chain: List of option records with bid, ask, volume, open_interest.
        bwb_structure: Output from build_bwb_structure with legs, net_premium, max_loss.

    Returns:
        Dictionary with:
        - status: "PASS"|"WARN"|"FAIL"|"N/A"
        - checks: list of check results
        - valid: bool
    """
    result: dict[str, Any] = {
        "status": "N/A",
        "checks": [],
        "valid": False,
    }

    try:
        if not isinstance(bwb_structure, dict) or not bwb_structure.get("valid", False):
            result["checks"].append({
                "name": "structure_valid",
                "status": "FAIL",
                "detail": "BWB structure is invalid or missing.",
            })
            return result

        legs = bwb_structure.get("legs", [])
        if not legs:
            result["checks"].append({
                "name": "legs_present",
                "status": "FAIL",
                "detail": "No legs found in BWB structure.",
            })
            return result

        chain_map = _build_chain_map(option_chain)

        for leg in legs:
            strike = leg.get("strike")
            opt_type = leg.get("type", "").lower()
            chain_key = (strike, opt_type)
            chain_option = chain_map.get(chain_key)

            spread_check = _check_spread(leg, chain_option)
            result["checks"].append(spread_check)

            mid_check = _check_mid_sanity(leg, chain_option)
            result["checks"].append(mid_check)

            liquidity_check = _check_liquidity(leg, chain_option)
            result["checks"].append(liquidity_check)

            delta_check = _check_delta_present(leg)
            result["checks"].append(delta_check)

        credit_check = _check_credit_threshold(bwb_structure)
        result["checks"].append(credit_check)

        max_loss_check = _check_max_loss_cap(bwb_structure)
        result["checks"].append(max_loss_check)

        result["status"] = _compute_overall_status(result["checks"])
        result["valid"] = True

        return result

    except Exception:
        result["checks"].append({
            "name": "evaluation_error",
            "status": "FAIL",
            "detail": "Unexpected error during quality evaluation.",
        })
        return result


def _build_chain_map(
    option_chain: list[dict[str, Any]] | None,
) -> dict[tuple[float, str], dict[str, Any]]:
    """Build lookup map from (strike, type) to option data."""
    if not option_chain:
        return {}

    chain_map = {}
    for opt in option_chain:
        strike = opt.get("strike")
        opt_type = opt.get("type", "").lower()
        if strike is not None:
            chain_map[(strike, opt_type)] = opt
    return chain_map


def _check_spread(
    leg: dict[str, Any],
    chain_option: dict[str, Any] | None,
) -> dict[str, Any]:
    """Check bid-ask spread width for a leg."""
    strike = leg.get("strike", "?")
    name = f"spread_{strike}"

    if chain_option is None:
        return {
            "name": name,
            "status": "WARN",
            "detail": f"Strike {strike}: No chain data to verify spread.",
        }

    bid = chain_option.get("bid")
    ask = chain_option.get("ask")

    if bid is None or ask is None:
        return {
            "name": name,
            "status": "WARN",
            "detail": f"Strike {strike}: Bid/ask missing.",
        }

    spread = ask - bid

    if spread <= 0.50:
        return {
            "name": name,
            "status": "PASS",
            "detail": f"Strike {strike}: Spread ${spread:.2f} (tight)",
        }
    elif spread <= 1.00:
        return {
            "name": name,
            "status": "WARN",
            "detail": f"Strike {strike}: Spread ${spread:.2f} (moderate)",
        }
    else:
        return {
            "name": name,
            "status": "FAIL",
            "detail": f"Strike {strike}: Spread ${spread:.2f} (wide)",
        }


def _check_mid_sanity(
    leg: dict[str, Any],
    chain_option: dict[str, Any] | None,
) -> dict[str, Any]:
    """Check that mid price is between bid and ask."""
    strike = leg.get("strike", "?")
    name = f"mid_sanity_{strike}"

    if chain_option is None:
        return {
            "name": name,
            "status": "WARN",
            "detail": f"Strike {strike}: No chain data for mid check.",
        }

    bid = chain_option.get("bid")
    ask = chain_option.get("ask")

    if bid is None or ask is None:
        return {
            "name": name,
            "status": "WARN",
            "detail": f"Strike {strike}: Bid/ask missing for mid check.",
        }

    mid = (bid + ask) / 2.0

    if bid <= mid <= ask:
        return {
            "name": name,
            "status": "PASS",
            "detail": f"Strike {strike}: Mid ${mid:.2f} valid.",
        }
    else:
        return {
            "name": name,
            "status": "FAIL",
            "detail": f"Strike {strike}: Mid ${mid:.2f} outside bid/ask.",
        }


def _check_liquidity(
    leg: dict[str, Any],
    chain_option: dict[str, Any] | None,
) -> dict[str, Any]:
    """Check volume and open interest for liquidity."""
    strike = leg.get("strike", "?")
    name = f"liquidity_{strike}"

    if chain_option is None:
        return {
            "name": name,
            "status": "WARN",
            "detail": f"Strike {strike}: No chain data for liquidity check.",
        }

    volume = chain_option.get("volume")
    oi = chain_option.get("open_interest")

    if volume is None and oi is None:
        return {
            "name": name,
            "status": "WARN",
            "detail": f"Strike {strike}: Volume/OI data not available.",
        }

    volume = volume or 0
    oi = oi or 0

    if oi >= 200 or volume >= 50:
        return {
            "name": name,
            "status": "PASS",
            "detail": f"Strike {strike}: OI={oi}, Vol={volume} (liquid)",
        }
    else:
        return {
            "name": name,
            "status": "WARN",
            "detail": f"Strike {strike}: OI={oi}, Vol={volume} (thin)",
        }


def _check_delta_present(leg: dict[str, Any]) -> dict[str, Any]:
    """Check if delta is present on the leg."""
    strike = leg.get("strike", "?")
    name = f"delta_{strike}"
    delta = leg.get("delta")

    if delta is not None:
        return {
            "name": name,
            "status": "PASS",
            "detail": f"Strike {strike}: Delta={delta:.3f}",
        }
    else:
        return {
            "name": name,
            "status": "WARN",
            "detail": f"Strike {strike}: Delta missing.",
        }


def _check_credit_threshold(bwb_structure: dict[str, Any]) -> dict[str, Any]:
    """Check if net premium meets minimum threshold for credit structures."""
    name = "credit_threshold"
    net_premium = bwb_structure.get("net_premium", 0)
    structure_type = bwb_structure.get("structure_type", "")

    is_credit = "CREDIT" in structure_type.upper() or net_premium > 0

    if not is_credit:
        return {
            "name": name,
            "status": "PASS",
            "detail": "Debit structure - credit threshold N/A.",
        }

    if net_premium >= 1.50:
        return {
            "name": name,
            "status": "PASS",
            "detail": f"Net credit ${net_premium:.2f} meets threshold.",
        }
    else:
        return {
            "name": name,
            "status": "WARN",
            "detail": f"Net credit ${net_premium:.2f} below $1.50 threshold.",
        }


def _check_max_loss_cap(bwb_structure: dict[str, Any]) -> dict[str, Any]:
    """Check if max loss exceeds warning threshold."""
    name = "max_loss_cap"
    max_loss = bwb_structure.get("max_loss")

    if max_loss is None:
        return {
            "name": name,
            "status": "WARN",
            "detail": "Max loss unknown.",
        }

    if max_loss <= 3.50:
        return {
            "name": name,
            "status": "PASS",
            "detail": f"Max loss ${max_loss:.2f} within cap.",
        }
    else:
        return {
            "name": name,
            "status": "WARN",
            "detail": f"Max loss ${max_loss:.2f} exceeds $3.50 cap.",
        }


def _compute_overall_status(checks: list[dict[str, Any]]) -> str:
    """Compute overall status from individual checks."""
    has_fail = any(c["status"] == "FAIL" for c in checks)
    has_warn = any(c["status"] == "WARN" for c in checks)

    if has_fail:
        return "FAIL"
    elif has_warn:
        return "WARN"
    else:
        return "PASS"


if __name__ == "__main__":
    print("=" * 70)
    print("TEST 1: Good execution quality")
    print("-" * 70)

    chain = [
        {"type": "put", "strike": 5875, "bid": 26.00, "ask": 26.40, "volume": 100, "open_interest": 500},
        {"type": "put", "strike": 5900, "bid": 21.00, "ask": 21.30, "volume": 80, "open_interest": 400},
        {"type": "put", "strike": 5825, "bid": 38.00, "ask": 38.50, "volume": 60, "open_interest": 300},
    ]
    bwb = {
        "valid": True,
        "structure_type": "PUT_CREDIT_BWB",
        "legs": [
            {"action": "SELL", "quantity": 2, "type": "put", "strike": 5875, "price": 26.20, "delta": -0.55},
            {"action": "BUY", "quantity": 1, "type": "put", "strike": 5900, "price": 21.15, "delta": -0.50},
            {"action": "BUY", "quantity": 1, "type": "put", "strike": 5825, "price": 38.25, "delta": -0.65},
        ],
        "net_premium": 2.00,
        "max_loss": 3.00,
    }

    result = evaluate_execution_quality(chain, bwb)
    print(f"  status: {result['status']}")
    print(f"  valid: {result['valid']}")
    print("  checks:")
    for c in result["checks"]:
        print(f"    [{c['status']}] {c['name']}: {c['detail']}")

    print("\n" + "=" * 70)
    print("TEST 2: Wide spreads and thin liquidity")
    print("-" * 70)

    chain2 = [
        {"type": "put", "strike": 5875, "bid": 25.00, "ask": 27.00, "volume": 5, "open_interest": 50},
    ]
    bwb2 = {
        "valid": True,
        "structure_type": "PUT_CREDIT_BWB",
        "legs": [
            {"action": "SELL", "quantity": 2, "type": "put", "strike": 5875, "price": 26.00},
        ],
        "net_premium": 0.80,
        "max_loss": 4.00,
    }

    result2 = evaluate_execution_quality(chain2, bwb2)
    print(f"  status: {result2['status']}")
    print("  checks:")
    for c in result2["checks"]:
        print(f"    [{c['status']}] {c['name']}: {c['detail']}")

    print("\n" + "=" * 70)
    print("TEST 3: Invalid structure")
    print("-" * 70)
    result3 = evaluate_execution_quality([], {"valid": False})
    print(f"  status: {result3['status']}")
    print(f"  checks: {result3['checks']}")
