# Portfolio Operating System v0.9

Capital OS now treats **survival + discipline + compounding** as the primary wealth objective.

The Portfolio Operating System contains four connected controls:

1. Investment Constitution
2. Portfolio Health
3. Benchmark & Attribution
4. Rebalancing Bands

## 1. Investment Constitution

The constitution is the policy layer above future agents and recommendations.

Default policy:

- horizon: 10 years;
- emergency reserve target: 6 months;
- max single position: 15%;
- max sector: 30%;
- max Opportunity bucket: 20%;
- max Gold Lab bucket: 5%;
- drawdown tolerance: 25%;
- leverage: NONE;
- rebalance method: CONTRIBUTIONS_FIRST;
- benchmark: SPY;
- decision cooldown: 24 hours;
- Gold live execution: disabled.

The constitution is private and persisted in `tfm_investment_constitution`.

No AI agent should be allowed to bypass it merely because a signal looks attractive.

## 2. Portfolio Health

Route:

`/health`

API:

`POST /api/portfolio-health`

Current score is 0–100:

- Core integrity: 25
- Allocation discipline: 25
- Concentration discipline: 25
- Speculation discipline: 15
- Financial resilience: 10

Health states:

- 85–100: STRONG
- 70–84: HEALTHY_WITH_GAPS
- 50–69: NEEDS_ATTENTION
- <50: FRAGILE

The score is structural, not predictive. It does not claim the portfolio will outperform.

## 3. Benchmark & Attribution

v0.9 deliberately distinguishes two concepts:

### Current-holdings cost-basis return

This compares current market value with average-cost basis.

### Benchmark context

The engine retrieves the selected benchmark, by default SPY, over the constitution's comparison window.

The difference between the two is shown as **context only**.

It is not called alpha because exact portfolio performance requires:

- dated cash flows;
- daily/monthly portfolio snapshots;
- dividends;
- fees;
- FX;
- realized transactions.

Every explicit health evaluation now upserts a daily row to `tfm_portfolio_snapshots`. This starts the longitudinal history needed for future TWR/MWR.

Current attribution decomposes unrealized P&L by:

- bucket;
- current position.

It is labeled current-holdings attribution.

## 4. Rebalancing Bands

Each bucket has a target and a tolerance band.

Defaults:

- CORE: ±5 pp
- OPPORTUNITY: ±3 pp
- CASH: ±3 pp
- GOLD_LAB: ±2 pp

States:

- UNDERWEIGHT
- IN_BAND
- OVERWEIGHT

Default action policy:

- UNDERWEIGHT → DIRECT_NEW_CONTRIBUTIONS
- IN_BAND → HOLD_POLICY
- OVERWEIGHT → PAUSE_NEW_CONTRIBUTIONS

The engine does not sell automatically.

The default principle is **contributions first**: use new savings to repair drift before creating turnover, fees or tax events.

## Decision Memory

Each explicit evaluation can persist:

- exact inputs;
- health score;
- guardrails;
- benchmark context;
- attribution;
- rebalance state.

Tables:

- `tfm_portfolio_health_runs`
- `tfm_portfolio_snapshots`

All are private under user-level RLS.

## Known limitations

v0.9 does not yet calculate:

- sector exposure from issuer metadata;
- true TWR;
- XIRR/MWR;
- realized P&L;
- dividends;
- tax drag;
- FX-normalized return;
- factor exposure.

Those require richer transaction and reference data. The UI does not pretend otherwise.

## North star

The north star is not daily P&L.

It is the user's ability to:

- contribute consistently;
- keep Core intact;
- avoid concentration and leverage mistakes;
- rebalance with new cash;
- understand performance relative to a sensible benchmark;
- remain invested long enough for compounding to work.
