# Scalping Engine v0.3

## Product objective

Build an **event-driven intraday research and paper-trading system** for liquid markets such as:

- gold proxies / XAUUSD feeds;
- Nasdaq proxies / NQ, MNQ, QQQ feeds;
- highly liquid technology equities.

The system is designed so that the execution layer can be automated later, but **v0.3 only automates research and paper execution**.

The goal is not to maximize win rate in isolation. A strategy with a 70% win rate can still lose money if losses are much larger than wins.

### North-star metrics

1. net expectancy per trade;
2. net expectancy per unit of risk;
3. profit factor after spread/slippage/fees;
4. max drawdown;
5. return / drawdown;
6. turnover and cost drag;
7. out-of-sample stability;
8. risk-rule violations;
9. calibration of signal confidence.

## Important design choice: do not force constant trades

The system may evaluate the market continuously, but it should trade only when a setup passes the gates.

```text
continuous observation != continuous exposure
```

A scalper that forces 100 trades in a low-edge regime can lose to spread and slippage even if its directional calls are slightly better than random.

## Event loop

```text
new tick/bar
   ↓
market state
   ↓
indicator state
   ↓
regime filter
   ↓
setup detector
   ↓
signal score
   ↓
cost gate
   ↓
risk gate
   ↓
paper order
   ↓
position manager
   ↓
exit logic
   ↓
journal + attribution
```

## Signal stack

The first strategy family uses original implementations inspired by common concepts:

- ATR trailing trigger (UT-Bot-like concept);
- market structure / trend break;
- WaveTrend-style oscillator;
- Bollinger/Keltner squeeze state;
- EMA alignment;
- ATR volatility normalization.

No single indicator can open a position on its own.

## Entry state machine

```text
FLAT
 ↓
SETUP_FORMING
 ↓
READY
 ↓
PAPER_ENTER
 ↓
OPEN
 ↓
MANAGE
 ↓
EXIT
 ↓
COOLDOWN
 ↓
FLAT
```

## Long example

A long candidate can require:

- fast EMA > slow EMA;
- price above ATR trailing line;
- positive structure break;
- WaveTrend-style oscillator cross up;
- squeeze released or momentum expanding;
- spread/cost estimate below threshold;
- projected reward/risk above threshold.

Short is symmetric.

## Position exits

An open paper position can close because of:

1. hard stop;
2. profit target;
3. ATR trailing stop;
4. opposite regime;
5. maximum holding bars;
6. session close;
7. kill switch / daily loss limit.

## Cost model

Scalping must model:

```text
net_pnl =
gross_pnl
- spread
- commission
- estimated slippage
- financing if applicable
```

Every backtest without costs is considered diagnostic only.

## Risk policy

The deterministic risk gate owns the final decision.

Suggested research defaults:

- one position per symbol;
- fixed fractional risk in paper mode;
- max daily loss;
- max consecutive losses;
- cooldown after stop;
- max spread / ATR ratio;
- no averaging down;
- no martingale;
- news-event blackout can be added when an economic-calendar feed exists.

Parameters are strategy inputs, not promises of safe or profitable trading.

## Multi-market design

Each instrument gets its own configuration because microstructure differs.

```text
XAUUSD
  session emphasis: London / New York overlap
  cost model: FX/CFD spread + slippage
  volatility: high around macro releases

NQ / MNQ / QQQ
  session emphasis: US cash open + liquid futures hours
  cost model: futures/equity specific
  volatility: sensitive to rates and mega-cap tech

liquid tech equity
  session: exchange hours
  cost model: spread + fees + opening/closing auction effects
```

A signal calibrated on gold should not automatically be reused on Nasdaq.

## Autonomy roadmap

### A0 — Backtest
Historical bars only.

### A1 — Live observer
Streaming feed, no orders.

### A2 — Supervised paper scalper
System proposes; human approves paper orders.

### A3 — Autonomous paper scalper
System opens/closes simulated positions automatically.

### A4 — Shadow mode
Agent runs autonomously beside a live account but cannot route orders.

### A5 — Human-gated live workflow
The system can prepare a live ticket; a person remains responsible for submitting the real-money trade.

Advancement requires predefined evidence gates, not intuition.

## Evidence gate example

Do not promote a strategy unless it passes:

- sufficient trade count across multiple dates/regimes;
- positive net expectancy out of sample;
- cost stress test;
- walk-forward stability;
- acceptable drawdown;
- no dependence on one day/outlier;
- paper results consistent with backtest;
- latency/slippage measured in shadow mode.

## What the learning layer should answer

- Which setup has positive expectancy?
- Which market regime destroys it?
- Which timeframe works by instrument?
- Is the edge entry timing or exit management?
- How much P&L disappears after costs?
- Does a high confidence score actually mean higher realized expectancy?
- When should the system stay flat?
