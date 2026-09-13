# Market Intelligence + Learning Mode v0.8

## Product thesis

Capital OS should not imitate Bloomberg by maximizing the amount of information on screen.

It should optimize for:

1. relevance to the user's portfolio;
2. provenance;
3. explanation;
4. disciplined action;
5. education.

The daily workflow is:

```text
Daily Brief
   ↓
Market Intelligence
   ↓
Source Finder
   ↓
Portfolio context
   ↓
Capital Allocation
   ↓
Learning assignment
   ↓
Decision / Learning Memory
```

## Market Intelligence

Route: `/intelligence`

The default market map includes:

- SPY — broad US equities;
- QQQ — large-cap growth / Nasdaq;
- IWM — small caps;
- GLD — gold proxy;
- TLT — long-duration Treasuries;
- UUP — US dollar proxy;
- XLK, XLF, XLE, XLI, XLV, XLY, XLP — sector proxies.

Metrics:

- 1d / 5d / 20d / 60d return;
- 20d / 50d trend state;
- annualized 20d volatility;
- simple cross-asset regime;
- sector leaders / laggards.

User portfolio symbols and private watchlist symbols can be appended to the default universe.

## Macro Pulse

The backend reads official FRED series through the public CSV graph endpoint:

- DGS10 — US 10Y Treasury;
- DFII10 — US 10Y real yield;
- DFF — effective fed funds rate;
- T10Y2Y — 10Y–2Y spread.

Each card links back to the official FRED series page.

## Source Finder

The Source Finder is deliberately provenance-first.

Initial registry:

- SEC EDGAR;
- FRED;
- Investor.gov;
- U.S. Treasury;
- BLS;
- BEA;
- IBKR Traders' Academy;
- MIT OpenCourseWare.

Primary sources are ranked ahead of educational/secondary sources when they match the query.

Saved sources are private and stored in `tfm_source_bookmarks`.

## Daily Investor Brief

Route/API:

- `/api/daily-brief`
- rendered inside `/intelligence`

The brief is deterministic in v0.8. It does not ask a language model to hallucinate a market story.

It summarizes:

- market regime;
- sector leadership;
- QQQ vs SPY;
- small-cap breadth proxy;
- gold state;
- macro series;
- headlines for further investigation;
- a learning focus.

Headlines are discovery inputs. The UI explicitly encourages verification through primary sources.

## Learning Mode

Route: `/learning`

The first track is `beginner_investor`, free-first.

Initial sequence:

1. Investor.gov — investing basics;
2. Investor.gov — asset allocation/diversification;
3. Investor.gov — products, liquidity and costs;
4. IBKR Traders' Academy — market mechanics;
5. IBKR Traders' Academy — paper trading discipline;
6. MIT OpenCourseWare — present value / valuation;
7. MIT OpenCourseWare — risk and portfolio theory;
8. SEC EDGAR — reading primary filings;
9. FRED — macro data.

Each lesson includes an applied assignment.

Progress is persisted in `tfm_learning_progress`.

## AI investment committee: next layer

v0.8 creates the evidence substrate for future agents.

Planned roles:

- **Macro Agent** — explain rates, inflation, dollar and gold;
- **Portfolio Agent** — compare allocation against policy and goals;
- **Company Agent** — summarize primary filings and fundamentals;
- **Source Auditor** — require provenance and freshness;
- **Skeptic Agent** — challenge the dominant thesis;
- **Tutor Agent** — turn today's market into the next learning task.

The agents should never bypass the existing capital-allocation, risk, or execution guardrails.
