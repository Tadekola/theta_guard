# THETA-GUARD

A modular quantitative options trading system for systematic weekly SPX Broken Wing Butterfly (BWB) strategy evaluation.

## Overview

THETA-GUARD is a rule-based trading decision system that evaluates market conditions each week to determine whether to enter a defined-risk options spread. It emphasizes **capital preservation** over aggressive returns, using multiple gates and filters to block trades when conditions are unfavorable.

### Key Features

- **Holiday Gate** - Automatically detects market holidays and shortened weeks
- **EMA Engine** - Trend analysis using exponential moving averages
- **Entry Evaluator** - Multi-factor decision logic with hard blocks and signal checks
- **BWB Builder** - Constructs Broken Wing Butterfly spreads from option chains
- **Slippage Model** - Simulates execution costs at various fill assumptions
- **Risk Analysis** - Position sizing, gamma warnings, and max loss calculations
- **Weekly Journal** - Automatic logging of all decisions for forward testing
- **Streamlit Dashboard** - Visual interface for pipeline execution and monitoring

## Project Structure

```
theta_guard/
├── src/theta_guard/
│   ├── calendar/        # Holiday detection
│   ├── indicators/      # EMA and technical indicators
│   ├── signals/         # Entry evaluation and confidence scoring
│   ├── strategies/      # BWB structure building
│   ├── execution/       # Slippage and quality checks
│   ├── risk/            # Position sizing and gamma warnings
│   ├── journal/         # Weekly run logging
│   ├── live/            # Paper trading with Tradier API
│   └── run_week.py      # Main pipeline orchestrator
├── streamlit_app.py     # Dashboard UI
├── tests/               # Test suite
└── pyproject.toml       # Dependencies
```

## Installation

### Prerequisites

- Python 3.11+
- Poetry (recommended) or pip

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/theta-guard.git
cd theta-guard

# Install dependencies with Poetry
poetry install

# Or with pip
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in `src/theta_guard/` with:

```env
# Tradier API (required for live data)
TRADIER_TOKEN=your_api_token
TRADIER_BASE=https://api.tradier.com/v1/

# Mode settings
LIVE_MODE=true
```

## Usage

### Running the Dashboard

```bash
streamlit run streamlit_app.py
```

The dashboard provides:
- One-click pipeline execution
- Real-time market data display
- Trade/No-Trade decision with reasoning
- BWB structure visualization
- Slippage scenarios
- Weekly journal history

### Pipeline Flow

1. **Environment Validation** - Checks API credentials and mode settings
2. **Data Fetch** - Retrieves SPX prices and option chains from Tradier
3. **Holiday Check** - Determines if the week is tradeable
4. **EMA Analysis** - Computes trend state from price history
5. **Entry Evaluation** - Applies all decision rules
6. **Structure Building** - Constructs BWB if trade is allowed
7. **Advisory Layers** - Adds slippage, gamma, and confidence analysis
8. **Journaling** - Logs the decision for audit trail

## Decision Logic

The system uses a hierarchical decision process:

### Hard Blocks (Immediate NO TRADE)
- Holiday week detected
- Outside valid entry time window
- API/environment failures

### Signal Checks
- EMA trend alignment
- Volatility conditions
- Macro event awareness

### Trade Allowed
All gates must pass for a TRADE ALLOWED decision.

## Disclaimer

**This software is for educational and research purposes only.**

- Not financial advice
- No guarantee of profits
- Paper trading mode recommended
- Always understand the risks of options trading

## License

MIT License - See LICENSE file for details.
