# THETA-GUARD

A modular quantitative options **decision system** for evaluating a systematic weekly SPX Broken Wing Butterfly (BWB) strategy.

## Overview

THETA-GUARD is a rule-based trading decision engine that evaluates market conditions each week to determine whether a defined-risk options spread *should* be entered.  
It prioritizes **capital preservation, discipline, and transparency** over aggressive returns.

The system is designed to **block trades by default** and only allow participation when multiple independent conditions align.

> This project does **not** place trades automatically.  
> All outputs are advisory and intended for manual execution.

---

## Key Features

- **Holiday Gate** – Detects market holidays and shortened weeks
- **EMA Engine** – Short-term trend regime analysis (3 EMA / 8 EMA)
- **Entry Evaluator** – Hierarchical decision logic with hard blocks
- **BWB Builder** – Constructs Broken Wing Butterfly spreads from live option chains
- **Slippage Modeling** – Simulates realistic execution assumptions
- **Risk Analysis** – Position sizing guidance and gamma danger-zone warnings
- **Weekly Journal** – Append-only logging for forward testing and auditability
- **Streamlit Dashboard** – Read-only UI for decision explanation and monitoring

---

## What This Project Is NOT

- ❌ Not an auto-trading bot  
- ❌ Not a signal prediction system  
- ❌ Not a profit guarantee  
- ❌ Not optimized for high-frequency trading  

THETA-GUARD is intentionally conservative and slow by design.

---

## Project Structure

```
theta_guard/
├── src/theta_guard/
│   ├── calendar/        # Holiday detection
│   ├── indicators/      # EMA and technical indicators
│   ├── signals/         # Entry evaluation and confidence scoring
│   ├── strategies/      # BWB structure building
│   ├── execution/       # Slippage and execution quality checks
│   ├── risk/            # Position sizing and gamma warnings
│   ├── journal/         # Weekly run logging
│   ├── live/            # Paper trading with Tradier API
│   └── run_week.py      # Main pipeline orchestrator
├── streamlit_app.py     # Streamlit dashboard
├── tests/               # Test suite
└── pyproject.toml       # Dependencies
```

---

## Installation

### Prerequisites
- Python 3.11+
- Poetry (recommended)

### Setup

```bash
git clone https://github.com/yourusername/theta-guard.git
cd theta-guard
poetry install
```

### Environment Configuration

Create a `.env` file in the project root:

```env
# Tradier API (required for live market data)
TRADIER_TOKEN=your_api_token
TRADIER_BASE=https://api.tradier.com/v1/

# Runtime mode
LIVE_MODE=true
REQUIRE_HUMAN_APPROVAL=true
```

- `LIVE_MODE` enables live data access.
- Trades remain paper / advisory only.

---

## Usage

### Running the Dashboard

```bash
poetry run streamlit run streamlit_app.py
```

The dashboard provides:
- Manual pipeline evaluation (one run at a time)
- Trade / No-Trade decision with plain-English reasoning
- Recommended BWB structure (if allowed)
- Slippage-adjusted risk scenarios
- Gamma / danger-zone awareness
- Weekly decision history

### Typical Weekly Workflow

1. Open the dashboard near Monday market close
2. Review the TRADE ALLOWED / NO TRADE decision
3. If allowed, inspect risk and execution assumptions
4. Optionally execute the trade manually in your broker
5. Let the system journal the outcome automatically

---

## Decision Logic

THETA-GUARD uses a hierarchical decision process:

### Hard Blocks (Immediate NO TRADE)
- Market holiday or shortened week
- Invalid environment or missing data
- Outside permitted entry window

### Signal Conditions
- Short-term trend alignment (EMA regime)

### Advisory Context (Does NOT block trades)
- Slippage assumptions
- Gamma proximity warnings
- Macro / event annotations
- Confidence scoring

Only when all required gates pass does the system return **TRADE ALLOWED**.

---

## Disclaimer

**This software is for educational and research purposes only.**

- Not financial advice
- No guarantee of profits
- Options trading involves significant risk
- Use paper trading and small size when testing

---

## License

MIT License — see the [LICENSE](LICENSE) file for details.
