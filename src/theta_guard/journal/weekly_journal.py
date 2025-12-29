"""Automatic Weekly Journaling Module.

This module records every weekly run outcome for forward testing
and audit purposes.

ABSOLUTE RULES:
- Journaling ONLY
- Append-only
- No execution logic
- Fail-safe behavior (errors must not block system)
"""

import csv
import datetime
from pathlib import Path
from typing import Any

JOURNAL_FILENAME = "theta_guard_weekly_journal.csv"
JOURNAL_FIELDS = [
    "timestamp",
    "week",
    "mode",
    "decision",
    "bwb_valid",
    "reason_summary",
    "structure_type",
    "macro_events",
    "credit_mid",
    "credit_adj_5",
    "credit_adj_10",
    "credit_adj_15",
    "max_loss_mid",
    "max_loss_adj_5",
    "max_loss_adj_10",
    "max_loss_adj_15",
]


def log_weekly_run(run_result: dict[str, Any]) -> None:
    """Log the result of a weekly run to the journal CSV.

    Args:
        run_result: Output from paper_runner or live pipeline containing:
            - timestamp: str
            - mode: str
            - pipeline_result: dict (may be None)
            - env_validation: dict (optional, may be present)
    """
    try:
        # Extract data safely
        timestamp = run_result.get("timestamp", "")
        mode = run_result.get("mode", "UNKNOWN")
        
        # Calculate week from timestamp if possible, else use current
        week_str = _get_iso_week(timestamp)
        
        pipeline_result = run_result.get("pipeline_result")
        
        if pipeline_result:
            entry_decision = pipeline_result.get("entry_decision", {})
            decision = entry_decision.get("decision", "NO TRADE")
            
            bwb_structure = pipeline_result.get("bwb_structure")
            bwb_valid = bwb_structure.get("valid") if bwb_structure else None
            structure_type = bwb_structure.get("structure_type") if bwb_structure else None
            
            # Determine reason summary
            if decision == "TRADE ALLOWED":
                reason_summary = "All conditions met"
            else:
                reasons = entry_decision.get("reasons", [])
                if reasons:
                    reason_summary = str(reasons[0])
                else:
                    # Check env validation failures if pipeline result has reasons
                    # In paper_runner, env validation failure populates pipeline_result
                    reason_summary = "Unknown block reason"
                    
        else:
            # If pipeline_result is None, it might be an early env failure logged elsewhere?
            # Or just complete failure.
            # Check env_validation if available in run_result (added in previous step)
            env_val = run_result.get("env_validation")
            if env_val and not env_val.get("ok"):
                decision = "NO TRADE"
                bwb_valid = None
                structure_type = None
                reason_summary = f"Env Guard: {env_val.get('reason')}"
            else:
                decision = "ERROR"
                bwb_valid = None
                structure_type = None
                reason_summary = "Pipeline result missing"

        macro_events = _extract_macro_events(pipeline_result)
        slippage_data = _extract_slippage_data(run_result)

        row = {
            "timestamp": timestamp,
            "week": week_str,
            "mode": mode,
            "decision": decision,
            "bwb_valid": bwb_valid,
            "reason_summary": reason_summary,
            "structure_type": structure_type,
            "macro_events": macro_events,
            "credit_mid": slippage_data.get("credit_mid"),
            "credit_adj_5": slippage_data.get("credit_adj_5"),
            "credit_adj_10": slippage_data.get("credit_adj_10"),
            "credit_adj_15": slippage_data.get("credit_adj_15"),
            "max_loss_mid": slippage_data.get("max_loss_mid"),
            "max_loss_adj_5": slippage_data.get("max_loss_adj_5"),
            "max_loss_adj_10": slippage_data.get("max_loss_adj_10"),
            "max_loss_adj_15": slippage_data.get("max_loss_adj_15"),
        }
        
        _append_to_csv(row)

    except Exception:
        # Fail-safe: Journaling failure must NOT block execution
        pass


def _extract_macro_events(pipeline_result: dict[str, Any] | None) -> str:
    """Extract macro events as comma-separated string."""
    try:
        if not pipeline_result:
            return ""
        events = pipeline_result.get("macro_events", [])
        if isinstance(events, list):
            return ",".join(events)
        return ""
    except Exception:
        return ""


def _extract_slippage_data(run_result: dict[str, Any]) -> dict[str, Any]:
    """Extract slippage data for journaling."""
    data: dict[str, Any] = {
        "credit_mid": None,
        "credit_adj_5": None,
        "credit_adj_10": None,
        "credit_adj_15": None,
        "max_loss_mid": None,
        "max_loss_adj_5": None,
        "max_loss_adj_10": None,
        "max_loss_adj_15": None,
    }
    
    try:
        advisory = run_result.get("advisory", {})
        if not advisory:
            return data
            
        slippage = advisory.get("slippage_analysis", {})
        if not slippage or not slippage.get("valid"):
            return data
            
        scenarios = slippage.get("scenarios", {})
        
        s0 = scenarios.get("0pct", {})
        s5 = scenarios.get("5pct", {})
        s10 = scenarios.get("10pct", {})
        s15 = scenarios.get("15pct", {})
        
        data["credit_mid"] = s0.get("credit_mid")
        data["credit_adj_5"] = s5.get("credit_adjusted")
        data["credit_adj_10"] = s10.get("credit_adjusted")
        data["credit_adj_15"] = s15.get("credit_adjusted")
        
        data["max_loss_mid"] = s0.get("max_loss_mid")
        data["max_loss_adj_5"] = s5.get("max_loss_adjusted")
        data["max_loss_adj_10"] = s10.get("max_loss_adjusted")
        data["max_loss_adj_15"] = s15.get("max_loss_adjusted")
        
        return data
        
    except Exception:
        return data


def _get_iso_week(timestamp_str: str) -> str:
    """Extract ISO year-week from timestamp."""
    try:
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1]
        dt = datetime.datetime.fromisoformat(timestamp_str)
        year, week, _ = dt.isocalendar()
        return f"{year}-W{week:02d}"
    except (ValueError, TypeError):
        # Fallback to current week
        year, week, _ = datetime.datetime.utcnow().isocalendar()
        return f"{year}-W{week:02d}"


def _append_to_csv(row_data: dict[str, Any]) -> None:
    """Append a row to the CSV journal file."""
    # Locate project root (assuming this file is in src/theta_guard/journal/)
    # We want the file at project root (where pyproject.toml is)
    # This file: src/theta_guard/journal/weekly_journal.py
    # Parents: journal, theta_guard, src, PROJECT_ROOT
    project_root = Path(__file__).parent.parent.parent.parent
    file_path = project_root / JOURNAL_FILENAME
    
    file_exists = file_path.exists()
    
    with open(file_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=JOURNAL_FIELDS)
        
        if not file_exists:
            writer.writeheader()
            
        writer.writerow(row_data)


if __name__ == "__main__":
    print("=" * 60)
    print("JOURNALING MODULE TEST")
    print("=" * 60)
    
    # Test 1: TRADE ALLOWED
    test_result_1 = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "mode": "PAPER",
        "pipeline_result": {
            "entry_decision": {
                "decision": "TRADE ALLOWED",
                "reasons": []
            },
            "bwb_structure": {
                "valid": True,
                "structure_type": "PUT_CREDIT_BWB"
            }
        }
    }
    print("\nLogging Test 1 (TRADE ALLOWED)...")
    log_weekly_run(test_result_1)
    print("Done.")

    # Test 2: NO TRADE
    test_result_2 = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "mode": "PAPER",
        "pipeline_result": {
            "entry_decision": {
                "decision": "NO TRADE",
                "reasons": ["Holiday detected: New Year's Day"]
            },
            "bwb_structure": None
        }
    }
    print("\nLogging Test 2 (NO TRADE)...")
    log_weekly_run(test_result_2)
    print("Done.")
    
    # Verify file content
    print("\nVerifying journal content:")
    print("-" * 60)
    if Path(JOURNAL_FILENAME).exists():
        with open(JOURNAL_FILENAME, "r") as f:
            print(f.read())
    else:
        print("Error: Journal file not created.")

    # Cleanup
    try:
        Path(JOURNAL_FILENAME).unlink()
        print("\nCleanup: Journal file removed.")
    except Exception as e:
        print(f"Cleanup failed: {e}")
