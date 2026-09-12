# Agentic Market Lab v0.2

## Goal

Build an educational, evidence-first market agent that can:

1. observe markets continuously;
2. summarize what is leading/lagging;
3. identify regimes and factor rotations;
4. generate **paper-trading proposals** from explicit rules;
5. record whether a human accepts/rejects a proposal;
6. learn from subsequent outcomes;
7. compare human decisions vs. systematic decisions.

The system is intentionally split into **research**, **decision support**, **paper execution**, and **live read-only monitoring**.

## Autonomy ladder

### L0 — Market Observer
No decisions. Produces:
- trend;
- relative strength;
- realized volatility;
- breadth;
- sector leadership;
- cross-asset context.

### L1 — Research Agent
Produces structured insights such as:

> Technology is outperforming the broad market over 20/60 sessions while small caps lag.

No real-money orders.

### L2 — Supervised Paper Trader
The agent creates a proposal, e.g.:

- symbol: XLK
- action: PAPER_BUY
- hypothesis: relative-strength continuation
- invalidation: loss of 20-day trend
- confidence: medium
- evidence snapshot: stored

The user approves/rejects it.

### L3 — Autonomous Paper Trader
The same policy can execute automatically **only in the simulated paper broker**.

This is where we test whether autonomous behavior actually creates value.

### L4 — Live Read-only Monitor
Connect to MetaTrader 5 to read:
- account state;
- symbols/ticks;
- positions;
- historical deals;
- candles.

The research agent can compare real positions with its signals.

### L5 — Human-executed Live Trading
The system may prepare a trade ticket/checklist for the user, but the real-money transaction remains a separate human action.

## Architecture

```text
Public/market data
      │
      ▼
Market Snapshot
      │
      ├──────────────► Narrative / Regime Engine
      │                         │
      │                         ▼
      │                  Market Insights
      │
      ▼
Rule / Strategy Engine
      │
      ▼
Paper Proposal
      │
      ▼
Risk Policy Gate
      │
      ├── reject
      │
      ▼
Approval Queue ─────► approve / reject
      │
      ▼
Paper Broker
      │
      ▼
Outcome Store
      │
      ▼
Evaluation / Learning
```

## Core principle

The language model is **not the source of truth for execution**.

LLM responsibilities:
- explain;
- summarize;
- critique;
- generate hypotheses;
- compare scenarios.

Deterministic code responsibilities:
- prices;
- indicators;
- portfolio state;
- position sizing;
- risk limits;
- backtests;
- paper fills;
- performance attribution.

## Market insight examples

Instead of saying:

> Buy company X.

Prefer falsifiable observations:

- "XLK has positive 20d and 60d relative strength vs SPY."
- "XLE is losing momentum while GLD is strengthening."
- "IWM is below its 60d trend proxy; broad risk appetite is weaker than large-cap tech leadership."
- "The market currently rewards growth/technology more than small-cap cyclicals, based on relative-return proxies."

## Learning loop

Each proposal stores:

- timestamp;
- inputs known at that moment;
- feature values;
- rule fired;
- confidence;
- human decision;
- simulated fill;
- forward return after 1d/5d/20d;
- max adverse excursion;
- max favorable excursion;
- regime.

Then the system can answer:

- Which insights were useful?
- When did the human override improve results?
- Which regimes break the strategy?
- Does confidence correlate with outcomes?
- Are we over-trading?

## Safety / engineering guardrails

- paper broker is the only write-enabled broker in this repository;
- MetaTrader adapter is read-only;
- credentials never committed;
- every proposal is auditable;
- no hidden discretionary position sizing;
- no martingale;
- no averaging down by default;
- all strategy evaluation must include out-of-sample periods and costs.
