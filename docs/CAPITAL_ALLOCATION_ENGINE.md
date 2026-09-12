# Capital Allocation Engine v1

## Purpose

Translate a monthly contribution into an explainable **bucket-level proposal** without placing an order or moving money.

The engine connects:

- current portfolio market value;
- strategic target weights;
- active financial goals;
- written Opportunity theses;
- Gold Alpha evidence maturity.

It produces:

```text
monthly contribution
        ↓
goal cash overlay
        ↓
effective strategic targets
        ↓
post-contribution target gaps
        ↓
CORE / OPPORTUNITY / CASH / GOLD_LAB proposal
        ↓
explanation + guardrails
        ↓
Decision Memory
```

## Core rule

The engine does **not** choose a broker action.

It only answers:

> If I am contributing X units of my base currency, how should that contribution be distributed across my capital buckets given the policy and evidence I have already defined?

## Allocation logic

### 1. Goal overlay

A goal due within 24 months can reserve part of the monthly contribution in CASH.

The reserve is the smaller of:

- monthly amount required to close the goal shortfall;
- 30% of the current contribution.

Longer-horizon goals remain visible in diagnostics but do not override the strategic allocation.

### 2. Gold evidence gate

The user may define a strategic target for GOLD_LAB, but the engine only unlocks that target progressively.

```text
< 30 paper trades     DATA_COLLECTION       0% baseline unlock
30–99                 EARLY_EVIDENCE        up to 25%
100–299               PAPER_VALIDATION      up to 50%
300–499               ADVANCED_PAPER        up to 75%
500+                   MATURE_PAPER_SAMPLE   up to 100%
```

The baseline is then reduced if:

- expectancy is not positive;
- profit factor is below 1.20 or unavailable;
- drawdown exceeds the research tolerance;
- worker health is not confirmed.

This is deliberately conservative.

**Gold maturity only controls research-capital eligibility. It never authorizes live autonomous trading.**

### 3. Effective targets

If GOLD_LAB is not fully unlocked, the remaining strategic weights are renormalized across the other buckets.

This avoids forcing money into an unproven trading system merely because the original target says 5%.

### 4. Gap-based contribution allocation

After the goal overlay, the engine calculates the desired post-contribution value of every bucket and sends the remaining contribution toward the largest strategic shortfalls.

No existing position is sold.

### 5. Opportunity thesis gate

OPPORTUNITY remains a strategic bucket, but if fewer than 50% of active Opportunity positions have both:

- thesis;
- invalidation;

the proposed amount is marked `RESERVE_ONLY`.

The engine does not invent a stock to buy.

## Outputs

Each Allocation Run persists:

- exact inputs;
- portfolio value;
- contribution;
- effective targets;
- Gold stage and rigor;
- goal overlay;
- recommendation summary;
- one allocation item per bucket;
- rationale;
- deployment mode;
- guardrail.

Tables:

- `tfm_allocation_runs`
- `tfm_allocation_items`

Both are private under user-level RLS.

## Deployment modes

- `MANUAL`: bucket is eligible for manual deployment.
- `RESERVE_ONLY`: hold/earmark capital; thesis or goal conditions are incomplete.
- `RESEARCH_ONLY`: Gold research capital only; never a live-order permission.

## What this engine deliberately does not do

- no broker order;
- no exchange transaction;
- no transfer;
- no automatic security selection;
- no leverage decision;
- no automatic promotion of Gold Alpha to live money.

## North star

The engine is successful if it makes capital allocation **consistent, auditable and explainable**, not if every monthly recommendation maximizes short-term return.
