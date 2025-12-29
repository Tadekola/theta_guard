# THETA-GUARD Trading Charter

**Version:** 1.0  
**Status:** Active  
**Classification:** Non-Violable Constitution

---

## 1. Purpose

THETA-GUARD is a rules-based decision engine designed to determine whether a weekly SPX Broken Wing Butterfly (BWB) trade is permitted to be entered.

This charter defines the absolute rules governing all system behavior. All code, logic, and future modifications must conform to this document without exception.

The system prioritizes:

- Rule enforcement
- Statistical consistency
- Elimination of discretion

---

## 2. Instrument and Strategy Specification

| Parameter | Value |
|-----------|-------|
| Underlying | SPX only |
| Options Type | Cash-settled index options |
| Strategy | Broken Wing Butterfly (BWB) |
| Entry Day | Monday |
| Entry Time | End-of-day window (explicitly defined) |
| Expiration | Same-week Friday (target 4 DTE) |
| Position Management | Hold to expiration |
| Stop Losses | None |
| Profit Targets | None |

---

## 3. Hard Block Rules

Hard blocks are absolute. The system MUST return **NO TRADE** if ANY of the following conditions are true. Hard blocks override all signals, indicators, and other evaluations.

| # | Hard Block Condition |
|---|----------------------|
| 3.1 | Monday is a U.S. market holiday |
| 3.2 | Friday is a U.S. market holiday |
| 3.3 | Entry attempt occurs outside the defined Monday time window |
| 3.4 | Required market data is missing, stale, or inconsistent |
| 3.5 | The underlying is not SPX |
| 3.6 | Any rule in this charter cannot be conclusively evaluated |

**Precedence:** Hard blocks take absolute precedence. No signal condition, indicator state, or external input may override a hard block.

---

## 4. Signal Conditions

Signal conditions are necessary but not sufficient for trade entry. All of the following must be true to allow evaluation to proceed beyond the signal gate.

| # | Signal Condition |
|---|------------------|
| 4.1 | The 3-period EMA is above the 8-period EMA |
| 4.2 | The EMA timeframe is explicitly defined |
| 4.3 | The slope of the 8-period EMA is not negative at entry |

**Precedence:** Signal conditions do NOT override hard blocks. If all signal conditions are met but any hard block is triggered, the system returns NO TRADE.

---

## 5. Option Structure Rules

The following rules govern the construction of permitted option structures.

| # | Structure Rule |
|---|----------------|
| 5.1 | Only Broken Wing Butterfly structures are permitted |
| 5.2 | Risk must be fully defined at entry |
| 5.3 | Maximum loss must be known and finite |
| 5.4 | The structure must be asymmetric with favorable reward-to-risk |
| 5.5 | No discretionary strike selection outside defined rules |

---

## 6. Data and Determinism Requirements

All system operations must adhere to the following data integrity standards.

| # | Data Requirement |
|---|------------------|
| 6.1 | All indicators must be calculated deterministically |
| 6.2 | Data sources must be explicitly declared |
| 6.3 | Holiday calendars must be authoritative |
| 6.4 | If data ambiguity exists, the system must default to NO TRADE |

---

## 7. No Discretion Clause

THETA-GUARD does not permit discretionary overrides under any circumstance.

- Manual overrides are prohibited
- External signals cannot bypass rule evaluation
- If conditions are not met, the only valid action is NO TRADE
- Partial compliance is equivalent to non-compliance

---

## 8. Decision Output Specification

The system produces a binary decision with supporting context.

| Output | Meaning |
|--------|---------|
| **TRADE ALLOWED** | All hard blocks cleared, all signal conditions met, structure rules satisfied |
| **NO TRADE** | One or more hard blocks triggered, or one or more signal conditions not met |

Every decision must be accompanied by an evaluation record identifying which rules were evaluated and their pass/fail status.

---

## 9. Charter Governance

This charter is the authoritative source of truth for THETA-GUARD behavior.

- All code must implement these rules exactly as specified
- No code may introduce logic that contradicts this charter
- Amendments to this charter require explicit versioning and documentation
- In case of ambiguity between code and charter, the charter prevails

---

## 10. Definitions

| Term | Definition |
|------|------------|
| **Hard Block** | An absolute condition that, if triggered, results in NO TRADE regardless of all other factors |
| **Signal Condition** | A required condition that must be met for trade consideration, but does not override hard blocks |
| **BWB** | Broken Wing Butterfly, an asymmetric options spread structure |
| **DTE** | Days to expiration |
| **EMA** | Exponential Moving Average |
| **SPX** | S&P 500 Index |

---

*End of Charter*
