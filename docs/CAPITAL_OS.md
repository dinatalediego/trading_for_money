# Capital OS v0.6

Capital OS connects two separate engines without mixing their mandates.

## Investment Engine

Purpose: build long-horizon wealth.

Persistent private data:

- accounts;
- portfolio positions;
- transaction ledger;
- goals;
- monthly contribution policy;
- target allocation across CORE / OPPORTUNITY / GOLD_LAB / CASH.

The browser authenticates directly with Supabase. Portfolio rows are protected by RLS using `owner_id = auth.uid()`.

Market values are enriched from the Vercel `/api/quotes` endpoint. A manual price is supported for assets that are not available from the research quote provider.

## Gold Alpha Engine

Purpose: search for incremental alpha under strict evidence gates.

It reads the existing persistent `tfm_*` Gold Worker memory:

- market snapshots;
- signal decisions;
- paper trades;
- forward outcomes;
- worker health;
- agent state.

It remains paper-only.

## Connection between engines

The connection is a **capital policy**, not shared execution.

```text
Investment Engine
      │
      ├── CORE
      ├── OPPORTUNITY
      ├── CASH
      └── GOLD_LAB allocation
                 │
                 ▼
          Gold Alpha Engine
                 │
         evidence / rigor gate
```

The portfolio interface explicitly communicates whether Gold Alpha is still collecting evidence or has earned a stronger research status. Increasing the GOLD_LAB allocation should not be automatic.

## Interface

Root route:

`/` → Capital OS

Gold trading terminal:

`/gold`

The Capital OS root includes:

- authenticated private portfolio;
- live/recent quote enrichment;
- target-vs-actual allocation;
- contribution policy;
- goals;
- Portfolio Brief generated from real connected records;
- Gold Alpha paper stats;
- worker health;
- recent decisions;
- recent paper trades;
- a Rigor Score based on sample size, expectancy, risk discipline, and worker health.
