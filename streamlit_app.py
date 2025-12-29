"""THETA-GUARD Streamlit UI.

A READ-ONLY decision and explanation console for the THETA-GUARD system.
This UI explains the decisions made by the engine but never executes trades.

Run with:
    streamlit run streamlit_app.py
"""

import sys
import csv
import datetime
from pathlib import Path
from typing import Any, List, Dict

# --- ENV LOADING ---
try:
    from dotenv import load_dotenv
    import os
    
    # Try loading from src/theta_guard/.env (where user keeps it)
    # Now Path is imported and available
    env_path = Path(__file__).parent / "src" / "theta_guard" / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        # Fallback to default search
        load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, continue silently

import streamlit as st
import pandas as pd

# Ensure src is in python path
PROJECT_ROOT = Path(__file__).parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

try:
    from theta_guard.live.paper_runner import run_paper_pipeline
    from theta_guard.risk.position_sizing import recommend_position_size, compute_risk_metrics
    from theta_guard.execution.slippage_model import format_slippage_table
except ImportError:
    # Fallback for when running in an environment where installation is partial
    # This expects the user to have run `poetry install`
    st.error("Could not import theta_guard. Please ensure you are running this from the project root and dependencies are installed.")
    st.stop()

# --- CONSTANTS ---
JOURNAL_FILE = PROJECT_ROOT / "theta_guard_weekly_journal.csv"

st.set_page_config(
    page_title="THETA-GUARD",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# --- CSS STYLES ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E1E1E;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555555;
        margin-bottom: 2rem;
    }
    .decision-box {
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 1rem;
    }
    .decision-trade {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .decision-no-trade {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    .decision-title {
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
    }
    .decision-reason {
        font-size: 1.1rem;
        margin-top: 0.5rem;
        font-style: italic;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)


def load_journal() -> pd.DataFrame:
    """Load the weekly journal CSV."""
    if not JOURNAL_FILE.exists():
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(JOURNAL_FILE)
        # Sort by timestamp desc
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp", ascending=False)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)  # Cache for 5 minutes
def run_pipeline_cached() -> Dict[str, Any]:
    """Run the pipeline and cache result to avoid spamming API."""
    try:
        # We use a wrapper to allow caching
        return run_paper_pipeline()
    except Exception as e:
        # FAIL-SAFE: Return a structure that indicates failure but allows UI to render
        return {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "mode": "PAPER",
            "pipeline_result": None,
            "env_validation": {
                "ok": False, 
                "reason": f"Pipeline Crash: {str(e)}"
            }
        }


# --- HELPERS ---
def safe_get_dict(obj: Any, key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary, handling None obj."""
    if obj is None or not isinstance(obj, dict):
        return default
    return obj.get(key, default)


def safe_bool(obj: Any) -> bool:
    """Safely convert object to boolean, handling None."""
    if obj is None:
        return False
    return bool(obj)


def safe_float(obj: Any, default: float = 0.0) -> float:
    """Safely convert object to float, handling None and strings."""
    if obj is None:
        return default
    try:
        return float(obj)
    except (ValueError, TypeError):
        return default


def main():
    # --- SIDEBAR: Position Sizing Inputs ---
    with st.sidebar:
        st.markdown("### 💰 Position Sizing")
        st.caption("Advisory inputs for risk management")
        
        account_size = st.number_input(
            "Account Size ($)",
            min_value=0.0,
            max_value=10000000.0,
            value=0.0,
            step=1000.0,
            help="Your total trading account value"
        )
        
        max_risk_pct = st.slider(
            "Max Risk (%)",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1,
            help="Maximum percentage of account to risk per trade"
        ) / 100.0
        
        st.divider()
        st.caption("These are advisory inputs only. No orders are placed.")

    # --- HEADER ---
    st.markdown('<div class="main-header">🛡️ THETA-GUARD</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Weekly SPX Decision Engine</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"Last Updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # --- RUN PIPELINE ---
    with st.spinner("Consulting the Oracle... (Running Live Pipeline)"):
        # Force refresh button
        if st.button("Refresh Pipeline"):
            run_pipeline_cached.clear()
            
        result = run_pipeline_cached()

    # Use helpers to extract data safely
    pipeline_result = safe_get_dict(result, "pipeline_result")
    env_validation = safe_get_dict(result, "env_validation")
    
    # Update Status Badge based on Environment Validation
    with col2:
        if env_validation and safe_bool(safe_get_dict(env_validation, "ok")):
             st.markdown("### :green[● LIVE DATA]")
        else:
             st.markdown("### :grey[○ PAPER MODE]")
    
    # --- SECTION 2: FINAL DECISION ---
    decision = "NO TRADE"
    reason_text = "Unknown error."
    pipeline_data = None
    
    # Determine Status
    if env_validation and not safe_bool(safe_get_dict(env_validation, "ok")):
        decision = "NO TRADE"
        reason_text = f"Environment Guard: {safe_get_dict(env_validation, 'reason', 'Unknown failure')}"
        pipeline_data = None
    elif pipeline_result:
        entry_decision = safe_get_dict(pipeline_result, "entry_decision", {})
        decision = safe_get_dict(entry_decision, "decision", "NO TRADE")
        
        if decision == "TRADE ALLOWED":
            reason_text = "All hard blocks passed and EMA conditions are bullish."
        else:
            reasons = safe_get_dict(entry_decision, "reasons", [])
            reason_text = reasons[0] if reasons else "Conditions not met."
        
        pipeline_data = pipeline_result
    else:
        # Fallback if pipeline returned success structure but no result (e.g. data fetch fail handled internally)
        decision = "NO TRADE"
        reason_text = "Decision Context unavailable due to data fetch failure."
        pipeline_data = None

    # Render Decision Box
    if decision == "TRADE ALLOWED":
        st.markdown(f"""
        <div class="decision-box decision-trade">
            <div class="decision-title">🟢 TRADE ALLOWED</div>
            <div class="decision-reason">{reason_text}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="decision-box decision-no-trade">
            <div class="decision-title">🔴 NO TRADE</div>
            <div class="decision-reason">{reason_text}</div>
        </div>
        """, unsafe_allow_html=True)

    # --- SECTION 3: EXPLANATION ---
    st.markdown("### 🧠 Decision Context")
    
    # Only render details if we have valid pipeline data
    if pipeline_data:
        holiday = safe_get_dict(pipeline_data, "holiday_result", {})
        ema = safe_get_dict(pipeline_data, "ema_state", {})
        entry = safe_get_dict(pipeline_data, "entry_decision", {})
        
        # Hard Blocks
        # Only show if holiday result exists (proxy for valid initial data)
        if holiday:
            with st.expander("Hard Blocks (Must ALL Pass)", expanded=True):
                blocks = safe_get_dict(entry, "hard_blocks_triggered", [])
                
                # Holiday
                is_trade_week = safe_bool(safe_get_dict(holiday, "is_trade_week", False))
                icon = "✅" if is_trade_week else "❌"
                st.markdown(f"{icon} **Holiday Check**: {safe_get_dict(holiday, 'reason', 'N/A')}")
                
                # EMA Validity
                ema_valid = safe_bool(safe_get_dict(ema, "valid", False))
                icon = "✅" if ema_valid else "❌"
                st.markdown(f"{icon} **Data Sufficiency**: {'Enough data for EMA' if ema_valid else 'Insufficient data'}")
                
                # Entry Time
                time_fail = "entry_time_valid" in blocks if blocks else False
                icon = "❌" if time_fail else "✅"
                st.markdown(f"{icon} **Entry Window**: {'Market open' if not time_fail else 'Closed'}")

        # Signal Conditions
        # Only show if EMA data exists
        if ema:
            with st.expander("Signal Conditions", expanded=True):
                failures = safe_get_dict(entry, "signal_failures", [])
                
                # Short > Long
                short_above = safe_bool(safe_get_dict(ema, "short_above_long", False))
                icon = "✅" if short_above else "❌"
                msg = "Bullish alignment" if short_above else "Bearish alignment"
                st.markdown(f"{icon} **Trend (3 > 8 EMA)**: {msg}")
                st.caption("The short-term trend must be above the long-term trend.")
                
                # Slope
                raw_slope = safe_get_dict(ema, "long_ema_slope", 0.0)
                slope = safe_float(raw_slope)
                
                slope_fail = "long_ema_slope_negative" in failures if failures else False
                icon = "❌" if slope_fail else "✅"
                st.markdown(f"{icon} **Momentum (Slope)**: {slope:.4f}")
                st.caption("The 8-day EMA slope must not be negative.")
        else:
             st.info("Signal data unavailable.")

    else:
        st.info("Detailed decision context is unavailable (likely due to data fetch issues).")

    # --- SECTION 4: TRADE RECOMMENDATION ---
    if decision == "TRADE ALLOWED" and pipeline_data:
        st.markdown("### 🎫 Trade Recommendation")
        bwb = safe_get_dict(pipeline_data, "bwb_structure", {})
        
        if bwb and safe_bool(safe_get_dict(bwb, "valid")):
            st.info(f"**Strategy**: {safe_get_dict(bwb, 'structure_type', 'Unknown').replace('_', ' ')}")
            
            # Legs Table
            legs = safe_get_dict(bwb, "legs", [])
            if legs:
                leg_data = []
                for leg in legs:
                    leg_data.append({
                        "Action": f"{safe_get_dict(leg, 'action')} {safe_get_dict(leg, 'quantity')}x",
                        "Type": safe_get_dict(leg, 'type', '').upper(),
                        "Strike": safe_get_dict(leg, 'strike'),
                        "Est. Price": f"${safe_float(safe_get_dict(leg, 'price', 0)):.2f}"
                    })
                st.table(pd.DataFrame(leg_data))
            
            # Metrics
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Net Premium", f"${safe_float(safe_get_dict(bwb, 'net_premium', 0)):.2f}")
            with c2:
                st.metric("Max Loss", f"${safe_float(safe_get_dict(bwb, 'max_loss', 0)):.2f}")
                
            st.caption("⚠️ Strikes selected using delta rules defined in the charter.")
        else:
            st.error("Trade allowed but structure generation failed.")

    # --- SECTION 5: LIVE OPTIONS CONTEXT ---
    if decision == "TRADE ALLOWED" and pipeline_data:
        st.markdown("### 📊 Options Context (Selected Legs)")
        st.caption("Displaying details for selected legs from the option chain.")
        
        bwb = safe_get_dict(pipeline_data, "bwb_structure", {})
        legs = safe_get_dict(bwb, "legs", [])
        if legs:
            for leg in legs:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**{safe_get_dict(leg, 'strike')} {safe_get_dict(leg, 'type', '').upper()}**")
                with col2:
                    st.markdown(f"Delta: `{safe_get_dict(leg, 'delta', 'N/A')}`")
                with col3:
                    st.markdown(f"Price: `{safe_float(safe_get_dict(leg, 'price', 0)):.2f}`")
                st.divider()

    # --- SECTION 6: ADVISORY LAYERS (only when TRADE ALLOWED) ---
    advisory = safe_get_dict(result, "advisory", {})
    
    if decision == "TRADE ALLOWED" and advisory:
        st.markdown("---")
        st.markdown("## 📈 Advisory Layers")
        st.caption("Read-only analysis. Does NOT affect the trade decision.")
        
        # A) Confidence Score
        confidence = safe_get_dict(advisory, "confidence_score", {})
        if confidence and safe_bool(safe_get_dict(confidence, "valid")):
            with st.expander("🎯 Confidence Score", expanded=True):
                score = safe_float(safe_get_dict(confidence, "score", 0))
                grade = safe_get_dict(confidence, "grade", "N/A")
                
                grade_colors = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🔴", "N/A": "⚪"}
                grade_icon = grade_colors.get(grade, "⚪")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Score", f"{score:.1f} / 10")
                with col2:
                    st.markdown(f"### {grade_icon} Grade: **{grade}**")
                
                reasons = safe_get_dict(confidence, "reasons", [])
                if reasons:
                    st.markdown("**Scoring Factors:**")
                    for reason in reasons:
                        st.markdown(f"- {reason}")
        else:
            with st.expander("🎯 Confidence Score", expanded=False):
                st.info("Confidence score unavailable.")
        
        # B) Execution Quality
        exec_quality = safe_get_dict(advisory, "execution_quality", {})
        if exec_quality and safe_bool(safe_get_dict(exec_quality, "valid")):
            with st.expander("✅ Execution Quality", expanded=True):
                status = safe_get_dict(exec_quality, "status", "N/A")
                
                status_colors = {"PASS": "🟢", "WARN": "🟡", "FAIL": "🔴", "N/A": "⚪"}
                status_icon = status_colors.get(status, "⚪")
                
                st.markdown(f"### {status_icon} Overall: **{status}**")
                
                checks = safe_get_dict(exec_quality, "checks", [])
                if checks:
                    st.markdown("**Quality Checks:**")
                    for check in checks:
                        check_status = safe_get_dict(check, "status", "N/A")
                        check_icon = status_colors.get(check_status, "⚪")
                        detail = safe_get_dict(check, "detail", "")
                        st.markdown(f"- {check_icon} {detail}")
        else:
            with st.expander("✅ Execution Quality", expanded=False):
                st.info("Execution quality data unavailable.")
        
        # C) Gamma Warning
        gamma = safe_get_dict(advisory, "gamma_warning", {})
        if gamma and safe_bool(safe_get_dict(gamma, "valid")):
            with st.expander("⚡ Gamma / Danger Zone", expanded=True):
                level = safe_get_dict(gamma, "level", "N/A")
                
                level_colors = {"NORMAL": "🟢", "ELEVATED": "🟡", "HIGH": "🔴", "N/A": "⚪"}
                level_icon = level_colors.get(level, "⚪")
                
                st.markdown(f"### {level_icon} Risk Level: **{level}**")
                
                detail = safe_get_dict(gamma, "detail", "")
                if detail:
                    st.markdown(detail)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    distance = safe_get_dict(gamma, "distance")
                    st.metric("Distance to Short", f"{distance:.1f} pts" if distance else "N/A")
                with col2:
                    exp_move = safe_get_dict(gamma, "expected_move")
                    st.metric("Expected Move", f"{exp_move:.1f} pts" if exp_move else "N/A")
                with col3:
                    move_source = safe_get_dict(gamma, "move_source", "N/A")
                    st.metric("Move Source", move_source)
        else:
            with st.expander("⚡ Gamma / Danger Zone", expanded=False):
                st.info("Gamma warning data unavailable.")
    
    # --- SECTION 7: POSITION SIZING (always visible) ---
    st.markdown("---")
    st.markdown("### 💰 Position Sizing Advisory")
    
    bwb_for_sizing = safe_get_dict(pipeline_data, "bwb_structure", {}) if pipeline_data else {}
    max_loss = safe_get_dict(bwb_for_sizing, "max_loss")
    net_premium = safe_get_dict(bwb_for_sizing, "net_premium")
    
    if account_size > 0 and max_loss is not None and max_loss > 0:
        sizing = recommend_position_size(
            account_size=account_size,
            max_risk_pct=max_risk_pct,
            max_loss_per_contract=max_loss,
        )
        
        if safe_bool(safe_get_dict(sizing, "valid")):
            contracts = safe_get_dict(sizing, "contracts", 0)
            risk_budget = safe_get_dict(sizing, "risk_budget", 0)
            risk_used = safe_get_dict(sizing, "risk_used", 0)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Recommended Contracts", contracts)
            with col2:
                st.metric("Risk Budget", f"${risk_budget:,.2f}")
            with col3:
                st.metric("Risk Used", f"${risk_used:,.2f}")
            
            st.markdown(safe_get_dict(sizing, "detail", ""))
            
            forward_note = safe_get_dict(sizing, "forward_test_note")
            if forward_note:
                st.warning(forward_note)
            
            if contracts > 0 and net_premium is not None:
                metrics = compute_risk_metrics(
                    account_size=account_size,
                    max_loss_per_contract=max_loss,
                    net_premium_per_contract=net_premium,
                    contracts=contracts,
                )
                if safe_bool(safe_get_dict(metrics, "valid")):
                    with st.expander("📊 Risk Metrics Details"):
                        col1, col2 = st.columns(2)
                        with col1:
                            total_loss = safe_get_dict(metrics, "total_max_loss")
                            st.metric("Total Max Loss", f"${total_loss:,.2f}" if total_loss else "N/A")
                            acct_risk = safe_get_dict(metrics, "account_risk_pct")
                            st.metric("Account Risk %", f"{acct_risk:.2f}%" if acct_risk else "N/A")
                        with col2:
                            total_credit = safe_get_dict(metrics, "total_credit")
                            st.metric("Total Credit", f"${total_credit:,.2f}" if total_credit else "N/A")
                            rr = safe_get_dict(metrics, "reward_to_risk")
                            st.metric("Reward/Risk", f"{rr:.2f}" if rr else "N/A")
        else:
            st.info(safe_get_dict(sizing, "detail", "Unable to compute position size."))
    elif account_size <= 0:
        st.info("💡 Enter your account size in the sidebar to receive position sizing guidance.")
    else:
        st.info("Position sizing requires a valid trade structure with known max loss.")

    # --- SECTION 8: SLIPPAGE & FILL ASSUMPTIONS (only when TRADE ALLOWED) ---
    if decision == "TRADE ALLOWED" and advisory:
        slippage_analysis = safe_get_dict(advisory, "slippage_analysis", {})
        if slippage_analysis and safe_bool(safe_get_dict(slippage_analysis, "valid")):
            st.markdown("---")
            st.markdown("### 📉 Slippage & Fill Assumptions")
            st.caption("Real fills may differ from mid. This table shows conservative outcomes.")
            
            table_rows = format_slippage_table(slippage_analysis)
            if table_rows:
                slippage_df = pd.DataFrame(table_rows)
                slippage_df.columns = ["Slippage", "Credit", "Max Loss"]
                st.table(slippage_df)
            else:
                st.info("Slippage data unavailable.")

    # --- SECTION 9: MACRO / EVENT CONTEXT (always visible) ---
    st.markdown("---")
    st.markdown("### 🌍 Macro / Event Context")
    
    macro_events = []
    if pipeline_data:
        macro_events = safe_get_dict(pipeline_data, "macro_events", [])
    
    if macro_events and isinstance(macro_events, list) and len(macro_events) > 0:
        event_badges = " ".join([f"🏷️ **{event}**" for event in macro_events])
        st.markdown(event_badges)
        st.info("⚠️ Macro events can increase volatility. No trade rules are changed.")
    else:
        st.success("✅ No major macro events this week.")

    # --- SECTION 10: WEEKLY JOURNAL ---
    st.markdown("### 📜 Weekly Journal")
    journal_df = load_journal()
    
    if not journal_df.empty:
        # Show last 10
        display_df = journal_df.head(10)[["week", "decision", "reason_summary", "structure_type"]]
        st.table(display_df)
        st.caption("Consistency over time matters more than any single week.")
    else:
        st.warning("No journal history found. Run the pipeline to generate records.")

    # --- FOOTER / TOOLTIPS ---
    with st.expander("📚 Educational Notes"):
        st.markdown("""
        **Broken Wing Butterfly (BWB)**: A defined-risk option strategy used to generate income. 
        It typically involves buying one option, selling two options at a different strike, and buying one option at a further strike.
        
        **EMA (Exponential Moving Average)**: A technical indicator that places a greater weight and significance on the most recent data points.
        
        **No Trade Weeks**: It is normal and expected to sit on hands when conditions are not favorable. 
        Preserving capital is the primary goal.
        """)

if __name__ == "__main__":
    main()
