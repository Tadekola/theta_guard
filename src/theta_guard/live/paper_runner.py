"""Live Data Pipeline - Paper Mode (Tradier).

This module fetches REAL market data using the Tradier API
while strictly prohibiting any form of trade execution.

ABSOLUTE RULES:
- READ-ONLY API access ONLY
- NO order placement
- NO execution endpoints
- NO account mutation
- PAPER MODE ENFORCED

This module MUST NOT:
- Place trades
- Prepare orders
- Touch account endpoints
- Modify strategy logic
"""

import os
from datetime import datetime, timedelta
from typing import Any

import requests

from theta_guard.run_week import run_weekly_pipeline
from theta_guard.live.env_guard import validate_live_environment
from theta_guard.journal.weekly_journal import log_weekly_run
from theta_guard.signals.confidence_score import compute_confidence_score
from theta_guard.execution.quality_checks import evaluate_execution_quality
from theta_guard.risk.gamma_warning import compute_gamma_warning, extract_short_strike
from theta_guard.execution.slippage_model import compute_slippage_analysis

MODE = "PAPER"

TRADIER_HISTORY_ENDPOINT = "markets/history"
TRADIER_OPTIONS_ENDPOINT = "markets/options/chains"

SYMBOL_SPX = "SPX"
HISTORY_DAYS = 30

DEFAULT_STRUCTURE_TYPE = "PUT_CREDIT_BWB"


def run_paper_pipeline(
    entry_time_valid: bool = True,
    structure_type: str = DEFAULT_STRUCTURE_TYPE,
) -> dict[str, Any]:
    """Execute the THETA-GUARD pipeline in PAPER mode with live data.

    Fetches real market data from Tradier API and runs the full
    evaluation pipeline. NO trades are placed.

    Args:
        entry_time_valid: Whether entry time is within valid window.
        structure_type: BWB structure type ("PUT_CREDIT_BWB" or "CALL_DEBIT_BWB")

    Returns:
        Dictionary with:
        - timestamp: ISO8601 string
        - mode: "PAPER"
        - pipeline_result: dict from run_weekly_pipeline
    """
    result: dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": MODE,
        "pipeline_result": None,
        "env_validation": None,
    }

    try:
        env_check = validate_live_environment()
        result["env_validation"] = env_check

        if not env_check.get("ok", False):
            result["pipeline_result"] = _empty_pipeline_result(
                f"Environment validation failed: {env_check.get('reason', 'Unknown')}"
            )
            log_weekly_run(result)
            return result

        monday_date = _get_current_monday()

        prices = _fetch_spx_daily_closes()
        if not prices:
            result["pipeline_result"] = _empty_pipeline_result(
                "Failed to fetch SPX daily closes."
            )
            log_weekly_run(result)
            return result

        friday_expiration = _get_friday_expiration(monday_date)
        option_chain = _fetch_spx_option_chain(friday_expiration)

        pipeline_result = run_weekly_pipeline(
            monday_date=monday_date,
            entry_time_valid=entry_time_valid,
            prices=prices,
            option_chain=option_chain,
            structure_type=structure_type,
        )

        result["pipeline_result"] = pipeline_result

        advisory = _compute_advisory_layers(pipeline_result)
        result["advisory"] = advisory

        log_weekly_run(result)
        return result

    except Exception:
        result["pipeline_result"] = _empty_pipeline_result(
            "Unexpected error in paper pipeline."
        )
        log_weekly_run(result)
        return result


def _get_tradier_credentials() -> tuple[str, str]:
    """Get Tradier API credentials from environment."""
    token = os.environ.get("TRADIER_TOKEN", "")
    base_url = os.environ.get("TRADIER_BASE", "https://api.tradier.com/v1/")
    return token, base_url


def _get_current_monday() -> str:
    """Get the Monday of the current week as ISO date string."""
    today = datetime.utcnow().date()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    return monday.strftime("%Y-%m-%d")


def _get_friday_expiration(monday_date: str) -> str:
    """Get the Friday expiration date for the given Monday."""
    monday = datetime.strptime(monday_date, "%Y-%m-%d").date()
    friday = monday + timedelta(days=4)
    return friday.strftime("%Y-%m-%d")


def _fetch_spx_daily_closes() -> list[float]:
    """Fetch SPX daily closing prices from Tradier.

    Returns:
        List of closing prices (oldest to newest), or empty list on failure.
    """
    token, base_url = _get_tradier_credentials()

    if not token:
        return []

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=HISTORY_DAYS + 15)

    url = f"{base_url.rstrip('/')}/{TRADIER_HISTORY_ENDPOINT}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    params = {
        "symbol": SYMBOL_SPX,
        "interval": "daily",
        "start": start_date.strftime("%Y-%m-%d"),
        "end": end_date.strftime("%Y-%m-%d"),
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code != 200:
            return []

        data = response.json()
        
        history = data.get("history", {})
        if not history:
            return []

        days = history.get("day", [])
        if not days:
            return []

        if isinstance(days, dict):
            days = [days]

        closes: list[float] = []
        for day in days:
            close = day.get("close")
            if close is not None:
                closes.append(float(close))
        
        return closes

    except Exception:
        return []


def _fetch_spx_option_chain(expiration: str) -> list[dict[str, Any]]:
    """Fetch SPX option chain from Tradier.

    Args:
        expiration: Expiration date as YYYY-MM-DD

    Returns:
        Normalized list of option dicts, or empty list on failure.
    """
    token, base_url = _get_tradier_credentials()

    if not token:
        return []

    url = f"{base_url.rstrip('/')}/{TRADIER_OPTIONS_ENDPOINT}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    params = {
        "symbol": SYMBOL_SPX,
        "expiration": expiration,
        "greeks": "true",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code != 200:
            return []

        data = response.json()

        options_data = data.get("options", {})
        if not options_data:
            return []

        option_list = options_data.get("option", [])
        if not option_list:
            return []

        if isinstance(option_list, dict):
            option_list = [option_list]

        normalized = _normalize_option_chain(option_list)
        return normalized

    except Exception:
        return []


def _normalize_option_chain(
    raw_options: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize Tradier option data to standard format.

    Drops any option missing required fields.

    Args:
        raw_options: Raw option data from Tradier API

    Returns:
        List of normalized option dicts
    """
    normalized: list[dict[str, Any]] = []

    for opt in raw_options:
        try:
            option_type = opt.get("option_type", "").lower()
            strike = opt.get("strike")
            bid = opt.get("bid")
            ask = opt.get("ask")

            greeks = opt.get("greeks", {})
            delta = greeks.get("delta") if greeks else None

            if option_type not in ("call", "put"):
                continue
            if strike is None or bid is None or ask is None:
                continue
            if delta is None:
                continue

            normalized.append({
                "type": option_type,
                "strike": float(strike),
                "delta": float(delta),
                "bid": float(bid),
                "ask": float(ask),
            })

        except (ValueError, TypeError):
            continue

    return normalized


def _compute_advisory_layers(pipeline_result: dict[str, Any] | None) -> dict[str, Any]:
    """Compute all advisory layers from pipeline result.

    Advisory layers are READ-ONLY and do NOT affect trade decisions.
    If decision is NO TRADE, advisory fields are None.

    Returns:
        Dictionary with advisory data or None values.
    """
    advisory: dict[str, Any] = {
        "confidence_score": None,
        "execution_quality": None,
        "gamma_warning": None,
        "slippage_analysis": None,
    }

    try:
        if not pipeline_result:
            return advisory

        entry_decision = pipeline_result.get("entry_decision", {})
        decision = entry_decision.get("decision", "NO TRADE")

        if decision != "TRADE ALLOWED":
            return advisory

        ema_state = pipeline_result.get("ema_state")
        bwb_structure = pipeline_result.get("bwb_structure")
        spot_proxy = pipeline_result.get("spot_proxy")
        option_chain = pipeline_result.get("option_chain", [])

        advisory["confidence_score"] = compute_confidence_score(
            ema_state=ema_state,
            bwb_structure=bwb_structure,
            spot=spot_proxy,
            expected_move=None,
        )

        advisory["execution_quality"] = evaluate_execution_quality(
            option_chain=option_chain,
            bwb_structure=bwb_structure,
        )

        short_strike = extract_short_strike(bwb_structure)
        advisory["gamma_warning"] = compute_gamma_warning(
            spot=spot_proxy,
            short_strike=short_strike,
            expected_move=None,
        )

        net_premium = bwb_structure.get("net_premium") if bwb_structure else None
        max_loss = bwb_structure.get("max_loss") if bwb_structure else None
        advisory["slippage_analysis"] = compute_slippage_analysis(
            net_premium=net_premium,
            max_loss=max_loss,
        )

        return advisory

    except Exception:
        return advisory


def _empty_pipeline_result(reason: str) -> dict[str, Any]:
    """Return an empty pipeline result for failure cases."""
    return {
        "holiday_result": None,
        "ema_state": None,
        "entry_decision": {
            "decision": "NO TRADE",
            "hard_blocks_triggered": ["data_fetch_error"],
            "signal_failures": [],
            "reasons": [reason],
        },
        "bwb_structure": None,
        "spot_proxy": None,
        "option_chain": [],
        "macro_events": [],
    }


if __name__ == "__main__":
    import json

    result = run_paper_pipeline(
        entry_time_valid=True,
        structure_type="PUT_CREDIT_BWB",
    )

    output = {
        "timestamp": result["timestamp"],
        "mode": result["mode"],
        "decision": None,
        "bwb_valid": None,
    }

    pipeline = result.get("pipeline_result")
    if pipeline:
        entry = pipeline.get("entry_decision", {})
        output["decision"] = entry.get("decision", "NO TRADE")

        bwb = pipeline.get("bwb_structure")
        if bwb:
            output["bwb_valid"] = bwb.get("valid", False)

    print(json.dumps(output, indent=2))
