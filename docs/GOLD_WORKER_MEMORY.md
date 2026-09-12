# Gold Worker + Decision/Trade Memory v0.5

## Objective

Run the gold paper-trading research loop continuously without depending on an open browser.

The persistent worker observes the gold research feed every minute, stores the exact market state and decision, manages at most one paper position, and later labels each decision with realized forward outcomes.

## Runtime architecture

```text
Vercel Gold API
  /api/gold?interval=1m&range=1d
          │
          ▼
Supabase Postgres
  pg_cron: every minute
          │
          ▼
tfm_run_gold_worker()
          │
          ├── market snapshot
          ├── signal decision
          ├── paper trade lifecycle
          ├── risk state
          ├── 5m / 15m / 60m outcomes
          └── worker observability
```

The browser is now a control/visualization plane. The worker itself runs inside Supabase.

## Private memory tables

All tables have RLS enabled and no public policies by default.

- `tfm_market_snapshots`: exact observed market state.
- `tfm_signal_decisions`: auditable BUY / SELL / FLAT decision.
- `tfm_paper_trades`: persistent paper positions and closed trades.
- `tfm_decision_outcomes`: forward labels after 5m, 15m and 60m.
- `tfm_worker_runs`: heartbeat, errors and actions for every worker cycle.
- `tfm_agent_state`: aggregate persistent agent state and risk pause.

## Strategy v1

Current strategy key:

`gold_scalper_v1`

Current paper-entry gate:

- gold-only;
- 1-minute feed;
- `feed_state = LIVEISH`;
- BUY/SELL signal, never forced exposure;
- corresponding confluence score >= 75;
- one open position maximum;
- initial stop = signal plan stop;
- initial target = signal plan target.

Current exit gate:

- stop;
- target;
- opposite signal.

If stop and target are both touched in the same bar, the worker assumes the stop happened first. This is deliberately conservative.

## Risk controls

- no martingale;
- no averaging down;
- one position at a time;
- after four consecutive losing trades, paper entries pause for 60 minutes;
- browser state is not authoritative; Supabase is.

## Learning memory

Each non-FLAT decision with an entry price is evaluated at:

- +5 minutes;
- +15 minutes;
- +60 minutes.

The worker uses the first available bar at/after the requested horizon rather than the worker's current price. This allows later calibration of:

- signal confidence vs realized outcome;
- long-score / short-score usefulness;
- regime-specific edge;
- entry quality;
- decay of the signal over time.

## Important limitation

The current public gold feed is still a research proxy, not broker-native XAUUSD execution data.

Before any broker-shadow phase, replace the market source with broker-native bid/ask bars/ticks and calibrate:

- spread;
- commission;
- slippage;
- contract size;
- session behavior;
- latency.

## Promotion gates

Do not promote the strategy based only on win rate.

Track at minimum:

- paper trades;
- expectancy in R;
- profit factor;
- maximum drawdown;
- cost drag;
- out-of-sample stability;
- strategy performance by regime;
- error rate / missing worker cycles.
