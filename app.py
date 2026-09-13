from __future__ import annotations

import asyncio
import io
import math
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trading_for_money.scalping.backtest import BacktestConfig, run_backtest
from trading_for_money.scalping.costs import CostModel
from trading_for_money.scalping.strategy import ScalpingConfig, generate_signals
from trading_for_money.allocation import (
    AllocationInput,
    GoldEvidence,
    GoalInput,
    build_allocation_plan,
)
from trading_for_money.intelligence import (
    DEFAULT_MARKET_UNIVERSE,
    LEARNING_PATH,
    build_daily_brief,
    build_market_regime,
    compute_asset_metrics,
    find_sources,
)


app = FastAPI(
    title="Gold Scalping Intelligence",
    version="0.4.0",
    description="Gold-only research and paper-trading terminal.",
)

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
GOLD_RESEARCH_SYMBOL = "GC=F"
DEFAULT_STRATEGY = ScalpingConfig(
    fast_ema=20,
    slow_ema=50,
    atr_length=14,
    atr_mult=2.0,
    structure_lookback=20,
    min_score=70,
)


async def fetch_ohlcv(
    symbol: str = GOLD_RESEARCH_SYMBOL,
    *,
    interval: str = "1m",
    range_: str = "1d",
) -> tuple[pd.DataFrame, dict]:
    url = YAHOO_CHART.format(symbol=quote(symbol, safe=""))
    params = {
        "interval": interval,
        "range": range_,
        "includePrePost": "true",
        "events": "div,splits",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 GoldScalpingResearch/0.4",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=9.0, follow_redirects=True) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"market data provider error: {exc}") from exc

    chart = payload.get("chart", {})
    if chart.get("error"):
        raise HTTPException(status_code=502, detail=str(chart["error"]))

    results = chart.get("result") or []
    if not results:
        raise HTTPException(status_code=502, detail="market data provider returned no result")

    result = results[0]
    timestamps = result.get("timestamp") or []
    quotes = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    if not timestamps:
        raise HTTPException(status_code=502, detail="market data provider returned no bars")

    frame = pd.DataFrame(
        {
            "time": pd.to_datetime(timestamps, unit="s", utc=True),
            "open": quotes.get("open", []),
            "high": quotes.get("high", []),
            "low": quotes.get("low", []),
            "close": quotes.get("close", []),
            "volume": quotes.get("volume", []),
        }
    )
    frame = frame.set_index("time")
    frame = frame.dropna(subset=["open", "high", "low", "close"]).sort_index()

    if frame.empty:
        raise HTTPException(status_code=502, detail="no valid OHLC bars returned")

    return frame, result.get("meta") or {}


def safe_float(value):
    if value is None or pd.isna(value):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def bar_records(frame: pd.DataFrame, limit: int = 180) -> list[dict]:
    out = []
    for ts, row in frame.tail(limit).iterrows():
        out.append(
            {
                "time": int(ts.timestamp()),
                "open": safe_float(row["open"]),
                "high": safe_float(row["high"]),
                "low": safe_float(row["low"]),
                "close": safe_float(row["close"]),
            }
        )
    return out


def latest_signal_payload(signals: pd.DataFrame, meta: dict) -> dict:
    latest = signals.iloc[-1]
    signal = str(latest["signal"])
    price = float(latest["close"])
    atr_value = safe_float(latest["atr"])

    stop = target = None
    if atr_value and signal == "BUY":
        stop = price - 1.5 * atr_value
        target = price + 2.0 * atr_value
    elif atr_value and signal == "SELL":
        stop = price + 1.5 * atr_value
        target = price - 2.0 * atr_value

    ema_fast = safe_float(latest["ema_fast"])
    ema_slow = safe_float(latest["ema_slow"])
    atr_trend = int(latest["atr_trend"]) if pd.notna(latest["atr_trend"]) else 0

    if ema_fast is None or ema_slow is None:
        regime = "WARMING_UP"
    elif ema_fast > ema_slow and atr_trend > 0:
        regime = "TREND_UP"
    elif ema_fast < ema_slow and atr_trend < 0:
        regime = "TREND_DOWN"
    else:
        regime = "MIXED"

    bar_time = signals.index[-1]
    now = pd.Timestamp.now(tz="UTC")
    age_seconds = max(0.0, (now - bar_time).total_seconds())

    return {
        "symbol": GOLD_RESEARCH_SYMBOL,
        "instrument": "Gold futures research proxy",
        "price": price,
        "currency": meta.get("currency", "USD"),
        "exchange": meta.get("exchangeName"),
        "bar_time_utc": bar_time.isoformat(),
        "data_age_seconds": round(age_seconds, 1),
        "feed_state": "LIVEISH" if age_seconds <= 180 else "STALE_OR_MARKET_CLOSED",
        "signal": signal,
        "long_score": int(latest["long_score"]),
        "short_score": int(latest["short_score"]),
        "regime": regime,
        "atr": atr_value,
        "atr_pct": safe_float(latest["atr_pct"]),
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "wave": {
            "wt1": safe_float(latest["wt1"]),
            "wt2": safe_float(latest["wt2"]),
            "cross_up": bool(latest["wt_cross_up"]),
            "cross_down": bool(latest["wt_cross_down"]),
        },
        "squeeze": {
            "on": bool(latest["squeeze_on"]),
            "release": bool(latest["squeeze_release"]),
            "momentum": safe_float(latest["squeeze_momentum"]),
        },
        "structure": {
            "break_up": bool(latest["break_up"]),
            "break_down": bool(latest["break_down"]),
        },
        "plan": {
            "entry": price if signal in {"BUY", "SELL"} else None,
            "stop": stop,
            "target": target,
            "reward_to_risk": (2.0 / 1.5) if signal in {"BUY", "SELL"} else None,
            "mode": "PAPER_ONLY",
        },
    }


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "service": "gold-scalping-intelligence",
        "version": "0.8.0",
        "execution": "paper-only",
    }


@app.get("/api/gold")
async def gold_snapshot(
    interval: str = Query(default="1m", pattern="^(1m|2m|5m|15m)$"),
    range_: str = Query(default="1d", alias="range", pattern="^(1d|5d|1mo)$"),
):
    bars, meta = await fetch_ohlcv(interval=interval, range_=range_)
    if len(bars) < 65:
        raise HTTPException(
            status_code=422,
            detail=f"not enough bars for indicators: received {len(bars)}",
        )

    signals = generate_signals(bars, DEFAULT_STRATEGY)
    latest = latest_signal_payload(signals, meta)

    return {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "research_notice": (
            "GC=F is a research proxy. This feed is not broker execution-grade and may be delayed."
        ),
        "latest": latest,
        "bars": bar_records(signals),
    }


FRED_SERIES = {
    "DGS10": {
        "label": "US 10Y Treasury",
        "unit": "%",
        "source_url": "https://fred.stlouisfed.org/series/DGS10",
    },
    "DFII10": {
        "label": "US 10Y Real Yield",
        "unit": "%",
        "source_url": "https://fred.stlouisfed.org/series/DFII10",
    },
    "DFF": {
        "label": "Effective Fed Funds Rate",
        "unit": "%",
        "source_url": "https://fred.stlouisfed.org/series/DFF",
    },
    "T10Y2Y": {
        "label": "10Y–2Y Treasury Spread",
        "unit": "pp",
        "source_url": "https://fred.stlouisfed.org/series/T10Y2Y",
    },
}


async def fetch_fred_series(series_id: str) -> dict:
    meta = FRED_SERIES[series_id]
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                params={"id": series_id},
                headers={"user-agent": "capital-os-market-intelligence/0.8"},
            )
            response.raise_for_status()
        frame = pd.read_csv(io.StringIO(response.text))
        if series_id not in frame.columns:
            raise ValueError("series column missing")
        values = pd.to_numeric(frame[series_id], errors="coerce").dropna()
        if values.empty:
            raise ValueError("no numeric observations")
        latest_idx = values.index[-1]
        latest = float(values.iloc[-1])
        previous = float(values.iloc[-2]) if len(values) > 1 else latest
        date_value = str(frame.loc[latest_idx, frame.columns[0]])
        return {
            "series_id": series_id,
            "label": meta["label"],
            "value": latest,
            "previous": previous,
            "change": latest - previous,
            "unit": meta["unit"],
            "observation_date": date_value,
            "source": "FRED",
            "source_url": meta["source_url"],
        }
    except Exception as exc:
        return {
            "series_id": series_id,
            "label": meta["label"],
            "error": repr(exc),
            "source": "FRED",
            "source_url": meta["source_url"],
        }


async def fetch_market_news(query: str, limit: int = 6) -> list[dict]:
    url = "https://query1.finance.yahoo.com/v1/finance/search"
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                params={
                    "q": query,
                    "quotesCount": 0,
                    "newsCount": min(limit, 10),
                    "enableFuzzyQuery": "false",
                },
                headers={"user-agent": "capital-os-market-intelligence/0.8"},
            )
            response.raise_for_status()
            payload = response.json()
        out = []
        finance_terms = (
            "market", "stock", "shares", "s&p", "nasdaq", "fed", "federal reserve",
            "treasury", "yield", "rate", "inflation", "economy", "economic",
            "gold", "dollar", "bond", "earnings", "investor", "etf", "equity",
            "commodit", "oil", "company", "companies",
        )
        now_ts = int(pd.Timestamp.now(tz="UTC").timestamp())
        for item in (payload.get("news") or []):
            title = (item.get("title") or "").strip()
            published = item.get("providerPublishTime")
            age_ok = not published or (now_ts - int(published)) <= 3 * 24 * 3600
            relevant = any(term in title.lower() for term in finance_terms)
            if not (age_ok and relevant):
                continue
            out.append(
                {
                    "title": title,
                    "publisher": item.get("publisher"),
                    "url": item.get("link"),
                    "published_at": published,
                    "type": item.get("type"),
                    "source": "Yahoo Finance search",
                }
            )
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []


async def build_market_intelligence(extra_symbols: list[str] | None = None) -> dict:
    universe = dict(DEFAULT_MARKET_UNIVERSE)
    for symbol in extra_symbols or []:
        if symbol and symbol not in universe and len(universe) < 24:
            universe[symbol] = {"label": symbol, "group": "watchlist"}

    async def one(symbol: str, meta: dict):
        try:
            bars, provider_meta = await fetch_ohlcv(
                symbol,
                interval="1d",
                range_="6mo",
            )
            metrics = compute_asset_metrics(
                bars,
                symbol=symbol,
                label=meta["label"],
                group=meta["group"],
            )
            metrics["currency"] = provider_meta.get("currency", "USD")
            metrics["exchange"] = provider_meta.get("exchangeName")
            metrics["source"] = "Yahoo Finance research feed"
            metrics["source_url"] = f"https://finance.yahoo.com/quote/{quote(symbol, safe='')}/"
            return metrics
        except Exception as exc:
            return {
                "symbol": symbol,
                "label": meta["label"],
                "group": meta["group"],
                "error": str(exc),
            }

    metric_results = await asyncio.gather(
        *(one(symbol, meta) for symbol, meta in universe.items())
    )
    metrics = [x for x in metric_results if "error" not in x]
    errors = [x for x in metric_results if "error" in x]
    regime = build_market_regime(metrics)

    macro_results = await asyncio.gather(
        *(fetch_fred_series(series_id) for series_id in FRED_SERIES)
    )
    news_results = await asyncio.gather(
        fetch_market_news("S&P 500 Nasdaq Federal Reserve markets", 6),
        fetch_market_news("gold dollar Treasury yields Federal Reserve", 6),
    )
    headlines = []
    seen = set()
    for group in news_results:
        for item in group:
            key = (item.get("title"), item.get("url"))
            if key not in seen:
                seen.add(key)
                headlines.append(item)
    headlines = headlines[:8]

    return {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "regime": regime,
        "assets": metrics,
        "asset_errors": errors,
        "macro": macro_results,
        "headlines": headlines,
        "provenance": {
            "market_prices": "Yahoo Finance research feed",
            "macro": "FRED / Federal Reserve Bank of St. Louis",
            "news_discovery": "Yahoo Finance search",
            "method": (
                "Deterministic metrics from daily closes: 1d/5d/20d/60d returns, "
                "20d/50d trend and 20d annualized volatility."
            ),
        },
    }


@app.get("/api/market-intelligence")
async def market_intelligence(
    symbols: str = Query(default="", max_length=180),
):
    extra = []
    for raw in symbols.split(","):
        symbol = raw.strip().upper()
        if symbol and symbol not in extra:
            extra.append(symbol)
    return await build_market_intelligence(extra[:10])


@app.get("/api/daily-brief")
async def daily_investor_brief(
    symbols: str = Query(default="", max_length=180),
):
    extra = [x.strip().upper() for x in symbols.split(",") if x.strip()][:10]
    intelligence = await build_market_intelligence(extra)
    brief = build_daily_brief(
        intelligence["assets"],
        intelligence["regime"],
        macro=intelligence["macro"],
        headlines=intelligence["headlines"],
    )
    brief["generated_at"] = intelligence["generated_at"]
    brief["provenance"] = intelligence["provenance"]
    brief["source_shortcuts"] = find_sources(brief["learning_focus"], limit=5)
    return brief


@app.get("/api/source-finder")
async def source_finder(
    q: str = Query(default="", max_length=180),
):
    return {
        "query": q,
        "sources": find_sources(q, limit=8),
        "principle": (
            "Prefer primary/official sources for facts and filings; use aggregators "
            "for discovery, not as the final source of truth."
        ),
    }


@app.get("/api/learning-path")
async def learning_path():
    return {
        "track": "beginner_investor",
        "free_first": True,
        "lessons": LEARNING_PATH,
        "principle": (
            "Complete one resource at a time and connect each lesson to a real "
            "portfolio or paper-trading decision."
        ),
    }


class AllocationGoalRequest(BaseModel):
    name: str
    target_amount: float = Field(gt=0)
    target_date: str | None = None
    priority: int = Field(default=1, ge=1, le=5)


class AllocationGoldRequest(BaseModel):
    closed_trades: int = Field(default=0, ge=0)
    expectancy_r: float | None = None
    profit_factor: float | None = None
    max_drawdown_r: float | None = Field(default=None, ge=0)
    worker_healthy: bool = False


class AllocationRequest(BaseModel):
    contribution_amount: float = Field(ge=0)
    bucket_values: dict[str, float]
    target_weights: dict[str, float]
    goals: list[AllocationGoalRequest] = Field(default_factory=list)
    gold: AllocationGoldRequest = Field(default_factory=AllocationGoldRequest)
    opportunity_thesis_coverage: float = Field(default=0, ge=0, le=1)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)


@app.post("/api/allocation")
async def capital_allocation(request: AllocationRequest):
    from datetime import date

    try:
        goals = []
        for goal in request.goals:
            target_date = (
                date.fromisoformat(goal.target_date)
                if goal.target_date
                else None
            )
            goals.append(
                GoalInput(
                    name=goal.name,
                    target_amount=goal.target_amount,
                    target_date=target_date,
                    priority=goal.priority,
                )
            )

        plan = build_allocation_plan(
            AllocationInput(
                contribution_amount=request.contribution_amount,
                bucket_values=request.bucket_values,
                target_weights=request.target_weights,
                goals=tuple(goals),
                gold=GoldEvidence(
                    closed_trades=request.gold.closed_trades,
                    expectancy_r=request.gold.expectancy_r,
                    profit_factor=request.gold.profit_factor,
                    max_drawdown_r=request.gold.max_drawdown_r,
                    worker_healthy=request.gold.worker_healthy,
                ),
                opportunity_thesis_coverage=request.opportunity_thesis_coverage,
                base_currency=request.base_currency.upper(),
            )
        )
        return plan.to_dict()
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/quotes")
async def market_quotes(
    symbols: str = Query(default="", max_length=300),
):
    requested = []
    for raw in symbols.split(","):
        symbol = raw.strip().upper()
        if symbol and symbol not in requested:
            requested.append(symbol)
    if not requested:
        return {"quotes": {}}
    if len(requested) > 20:
        raise HTTPException(status_code=422, detail="maximum 20 symbols per request")

    quotes = {}
    for symbol in requested:
        try:
            bars, meta = await fetch_ohlcv(symbol, interval="1d", range_="5d")
            last = bars.iloc[-1]
            prev = bars.iloc[-2] if len(bars) > 1 else last
            price = safe_float(last["close"])
            previous = safe_float(prev["close"])
            change_pct = None
            if price is not None and previous not in (None, 0):
                change_pct = price / previous - 1
            quotes[symbol] = {
                "price": price,
                "previous_close": previous,
                "change_pct": change_pct,
                "currency": meta.get("currency", "USD"),
                "exchange": meta.get("exchangeName"),
                "market_time": bars.index[-1].isoformat(),
            }
        except Exception as exc:
            quotes[symbol] = {"error": str(exc)}
    return {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "quotes": quotes,
    }


@app.get("/api/backtest")
async def gold_backtest(
    interval: str = Query(default="5m", pattern="^(1m|2m|5m|15m)$"),
    range_: str = Query(default="5d", alias="range", pattern="^(1d|5d|1mo)$"),
    spread: float = Query(default=0.20, ge=0.0, le=10.0),
    slippage: float = Query(default=0.05, ge=0.0, le=10.0),
):
    bars, _ = await fetch_ohlcv(interval=interval, range_=range_)
    if len(bars) < 65:
        raise HTTPException(status_code=422, detail="not enough bars for backtest")

    trades, summary = run_backtest(
        bars,
        strategy=DEFAULT_STRATEGY,
        backtest=BacktestConfig(
            starting_cash=100_000.0,
            quantity=1.0,
            stop_atr=1.5,
            target_atr=2.0,
            max_holding_bars=20,
        ),
        costs=CostModel(
            spread=spread,
            slippage_per_side=slippage,
            commission_per_unit_round_trip=0.0,
        ),
    )

    recent = []
    if not trades.empty:
        recent = trades.tail(25).copy()
        for c in ["entry_time", "exit_time"]:
            recent[c] = recent[c].astype(str)
        recent = recent.to_dict(orient="records")

    return {
        "instrument": GOLD_RESEARCH_SYMBOL,
        "units_notice": (
            "P&L is expressed in research price-point units for quantity=1, not contract USD P&L."
        ),
        "assumptions": {
            "spread": spread,
            "slippage_per_side": slippage,
            "stop_atr": 1.5,
            "target_atr": 2.0,
        },
        "summary": summary,
        "recent_trades": recent,
    }


DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GOLD // Scalping Intelligence</title>
  <style>
    :root{
      --bg:#07090d;--panel:#0d1118;--panel2:#111722;--line:#202938;
      --text:#eef3f8;--muted:#7f8da0;--gold:#e8b949;--green:#41d39a;
      --red:#ff6577;--blue:#65a7ff;--orange:#ffb15c;
    }
    *{box-sizing:border-box}
    body{margin:0;background:radial-gradient(circle at 70% -20%,#182237 0,#07090d 38%);
      color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}
    .shell{max-width:1480px;margin:auto;padding:22px}
    .top{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}
    .brand{display:flex;align-items:center;gap:14px}.mark{width:42px;height:42px;border:1px solid #765f2b;
      border-radius:12px;display:grid;place-items:center;background:#17130b;color:var(--gold);font-weight:900}
    h1{font-size:18px;margin:0;letter-spacing:.08em}.sub{font-size:12px;color:var(--muted);margin-top:4px}
    .live{display:flex;gap:8px;align-items:center;color:var(--muted);font-size:12px}
    .dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 16px var(--green)}
    .grid{display:grid;grid-template-columns:minmax(0,2.1fr) minmax(330px,.9fr);gap:14px}
    .panel{background:linear-gradient(180deg,rgba(17,23,34,.95),rgba(10,14,21,.96));border:1px solid var(--line);
      border-radius:18px;box-shadow:0 12px 45px rgba(0,0,0,.25)}
    .pad{padding:18px}.charthead{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
    .symbol{font-size:14px;color:var(--muted)}.price{font-size:34px;font-weight:700;margin-top:3px;letter-spacing:-.04em}
    .pill{display:inline-flex;padding:7px 10px;border-radius:999px;font-size:11px;font-weight:800;letter-spacing:.07em;
      border:1px solid var(--line);background:#0a0e15}.buy{color:var(--green);border-color:#174b3d;background:#0b1a16}
    .sell{color:var(--red);border-color:#5b2530;background:#1e0e12}.flat{color:var(--orange);border-color:#5c4529;background:#1b150d}
    .timeframes{display:flex;gap:5px}.tf{border:1px solid var(--line);background:#0a0e15;color:var(--muted);
      padding:6px 9px;border-radius:8px;cursor:pointer;font-size:11px}.tf.active{color:#fff;border-color:#44526b;background:#172033}
    #chart{width:100%;height:450px;margin-top:12px;display:block}.axis{color:var(--muted)}
    .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px}.mini{padding:12px;border:1px solid var(--line);
      border-radius:12px;background:#0a0e15}.k{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
    .v{margin-top:5px;font-size:17px;font-weight:650}.signalbox{padding:18px}.bigsignal{font-size:38px;font-weight:850;letter-spacing:-.04em;margin:8px 0 3px}
    .scoregrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}.score{padding:13px;border:1px solid var(--line);
      border-radius:12px;background:#0a0e15}.bar{height:5px;background:#1a2230;border-radius:9px;margin-top:8px;overflow:hidden}
    .fill{height:100%;width:0;background:var(--green);transition:width .5s}.fill.short{background:var(--red)}
    .plan{margin-top:14px;border-top:1px solid var(--line);padding-top:14px}.row{display:flex;justify-content:space-between;gap:12px;
      padding:8px 0;font-size:13px}.row span:first-child{color:var(--muted)}.actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
    button.action{padding:11px;border-radius:10px;border:1px solid var(--line);font-weight:800;cursor:pointer;background:#111824;color:#fff}
    button.green{background:#0b251d;border-color:#1b614c;color:var(--green)}button.red{background:#2a1116;border-color:#742b38;color:var(--red)}
    button.gold{grid-column:1/-1;background:#241d0d;border-color:#806627;color:var(--gold)}
    .paper{margin-top:14px;padding:13px;border-radius:12px;border:1px solid var(--line);background:#0a0e15;font-size:12px}
    .bottom{display:grid;grid-template-columns:1.1fr .9fr;gap:14px;margin-top:14px}.metricline{display:grid;grid-template-columns:repeat(5,1fr);gap:9px}
    .notice{color:var(--muted);font-size:11px;line-height:1.45}.warning{color:#d7b96e}
    .loading{opacity:.55}.error{color:var(--red);white-space:pre-wrap}
    @media(max-width:980px){.grid,.bottom{grid-template-columns:1fr}.cards,.metricline{grid-template-columns:repeat(2,1fr)}#chart{height:340px}}
  </style>
</head>
<body>
<div class="shell">
  <div class="top">
    <div class="brand">
      <div class="mark">Au</div>
      <div><h1>GOLD // SCALPING INTELLIGENCE</h1><div class="sub">XAU research terminal · signals · paper execution · learning</div></div>
    </div>
    <div class="live"><span class="dot"></span><span id="feedState">CONNECTING</span><span id="clock"></span></div>
  </div>

  <div class="grid">
    <section class="panel pad">
      <div class="charthead">
        <div><div class="symbol">GC=F · GOLD FUTURES RESEARCH PROXY</div><div class="price" id="price">—</div><div class="sub" id="barTime">Waiting for market data…</div></div>
        <div class="timeframes">
          <button class="tf active" data-tf="1m">1m</button>
          <button class="tf" data-tf="2m">2m</button>
          <button class="tf" data-tf="5m">5m</button>
          <button class="tf" data-tf="15m">15m</button>
        </div>
      </div>
      <svg id="chart" viewBox="0 0 1000 450" preserveAspectRatio="none"></svg>
      <div class="cards">
        <div class="mini"><div class="k">Regime</div><div class="v" id="regime">—</div></div>
        <div class="mini"><div class="k">ATR / Price</div><div class="v" id="atrPct">—</div></div>
        <div class="mini"><div class="k">Wave</div><div class="v" id="wave">—</div></div>
        <div class="mini"><div class="k">Squeeze</div><div class="v" id="squeeze">—</div></div>
      </div>
    </section>

    <aside class="panel signalbox">
      <div class="k">Decision engine</div>
      <div class="bigsignal" id="signal">WAIT</div>
      <span class="pill flat" id="signalPill">STAY FLAT</span>

      <div class="scoregrid">
        <div class="score"><div class="row"><span>LONG</span><b id="longScore">0</b></div><div class="bar"><div class="fill" id="longFill"></div></div></div>
        <div class="score"><div class="row"><span>SHORT</span><b id="shortScore">0</b></div><div class="bar"><div class="fill short" id="shortFill"></div></div></div>
      </div>

      <div class="plan">
        <div class="k">Current paper plan</div>
        <div class="row"><span>Entry</span><b id="entry">—</b></div>
        <div class="row"><span>Stop</span><b id="stop">—</b></div>
        <div class="row"><span>Target</span><b id="target">—</b></div>
        <div class="row"><span>Reward / Risk</span><b id="rr">—</b></div>
      </div>

      <div class="actions">
        <button class="action green" onclick="paperOpen('BUY')">PAPER BUY</button>
        <button class="action red" onclick="paperOpen('SELL')">PAPER SELL</button>
        <button class="action gold" id="autoBtn" onclick="toggleAuto()">AUTO PAPER · OFF</button>
        <button class="action" style="grid-column:1/-1" onclick="paperClose('MANUAL')">CLOSE PAPER POSITION</button>
      </div>

      <div class="paper">
        <div class="k">Paper position</div>
        <div class="row"><span>Status</span><b id="paperStatus">FLAT</b></div>
        <div class="row"><span>Entry</span><b id="paperEntry">—</b></div>
        <div class="row"><span>Unrealized</span><b id="paperPnl">0.00</b></div>
        <div class="row"><span>Closed P&L</span><b id="closedPnl">0.00</b></div>
        <div class="notice">Browser-local simulation only. AUTO PAPER runs only while this page is open.</div>
      </div>
    </aside>
  </div>

  <div class="bottom">
    <section class="panel pad">
      <div class="k">5-day / 5-minute research backtest</div>
      <div class="metricline" style="margin-top:12px">
        <div class="mini"><div class="k">Trades</div><div class="v" id="btTrades">—</div></div>
        <div class="mini"><div class="k">Win rate</div><div class="v" id="btWin">—</div></div>
        <div class="mini"><div class="k">Profit factor</div><div class="v" id="btPf">—</div></div>
        <div class="mini"><div class="k">Net points</div><div class="v" id="btNet">—</div></div>
        <div class="mini"><div class="k">Max DD</div><div class="v" id="btDd">—</div></div>
      </div>
      <div class="notice warning" style="margin-top:12px">Backtest uses a simplified bar model and research costs. It is evidence, not a profitability guarantee.</div>
    </section>
    <section class="panel pad">
      <div class="k">Automation path</div>
      <div class="row"><span>0 · Signal research</span><b>ACTIVE</b></div>
      <div class="row"><span>1 · Browser paper auto</span><b>ACTIVE</b></div>
      <div class="row"><span>2 · Persistent paper worker</span><b>NEXT</b></div>
      <div class="row"><span>3 · Broker shadow mode</span><b>PLANNED</b></div>
      <div class="row"><span>4 · Human-gated live workflow</span><b>LOCKED</b></div>
      <div class="notice">For execution-grade XAUUSD we will replace this public research feed with a broker-native market gateway. Vercel remains the UI/control plane.</div>
    </section>
  </div>

  <div class="notice" style="margin:15px 3px 0">Research feed can be delayed. No real-money orders are sent from this application.</div>
  <div id="error" class="error"></div>
</div>

<script>
let tf='1m', snapshot=null;
let state=JSON.parse(localStorage.getItem('goldPaperState') || '{"position":null,"closedPnl":0,"auto":false}');
const fmt=(x,d=2)=>x==null?'—':Number(x).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d});

function save(){ localStorage.setItem('goldPaperState',JSON.stringify(state)); }
function setText(id,v){document.getElementById(id).textContent=v;}
function paperOpen(side){
  if(!snapshot || state.position) return;
  const p=snapshot.latest.price, atr=snapshot.latest.atr;
  if(!atr) return;
  state.position={side,entry:p,stop:side==='BUY'?p-1.5*atr:p+1.5*atr,target:side==='BUY'?p+2*atr:p-2*atr,openedAt:Date.now()};
  save(); renderPaper();
}
function paperClose(reason){
  if(!state.position || !snapshot) return;
  const p=snapshot.latest.price, q=state.position.side==='BUY'?1:-1;
  state.closedPnl += q*(p-state.position.entry);
  state.position=null; save(); renderPaper();
}
function toggleAuto(){state.auto=!state.auto;save();renderPaper();}

function autoPaperTick(){
  if(!snapshot || !state.auto) return;
  const x=snapshot.latest, pos=state.position;
  if(!pos){
    if(x.signal==='BUY' && x.long_score>=75) paperOpen('BUY');
    if(x.signal==='SELL' && x.short_score>=75) paperOpen('SELL');
    return;
  }
  const p=x.price;
  if(pos.side==='BUY' && (p<=pos.stop || p>=pos.target || x.signal==='SELL')) paperClose('RULE_EXIT');
  if(pos.side==='SELL' && (p>=pos.stop || p<=pos.target || x.signal==='BUY')) paperClose('RULE_EXIT');
}

function renderPaper(){
  const p=state.position, price=snapshot?.latest?.price;
  setText('autoBtn','AUTO PAPER · '+(state.auto?'ON':'OFF'));
  document.getElementById('autoBtn').style.color=state.auto?'var(--green)':'var(--gold)';
  setText('closedPnl',fmt(state.closedPnl));
  if(!p){setText('paperStatus','FLAT');setText('paperEntry','—');setText('paperPnl','0.00');return;}
  setText('paperStatus',p.side); setText('paperEntry',fmt(p.entry));
  if(price!=null){const q=p.side==='BUY'?1:-1;setText('paperPnl',fmt(q*(price-p.entry)));}
}

function drawChart(bars){
  const svg=document.getElementById('chart'); svg.innerHTML='';
  if(!bars || bars.length<2) return;
  const W=1000,H=450,pad=24;
  const lo=Math.min(...bars.map(b=>b.low)), hi=Math.max(...bars.map(b=>b.high)), range=(hi-lo)||1;
  const y=v=>pad+(hi-v)/range*(H-2*pad), x=i=>pad+i/(bars.length-1)*(W-2*pad);

  for(let g=0;g<5;g++){
    const yy=pad+g*(H-2*pad)/4;
    const line=document.createElementNS('http://www.w3.org/2000/svg','line');
    line.setAttribute('x1',pad);line.setAttribute('x2',W-pad);line.setAttribute('y1',yy);line.setAttribute('y2',yy);
    line.setAttribute('stroke','#182231');line.setAttribute('stroke-width','1');svg.appendChild(line);
  }
  const candleW=Math.max(1.2,Math.min(5,(W-2*pad)/bars.length*.65));
  bars.forEach((b,i)=>{
    const up=b.close>=b.open, color=up?'#41d39a':'#ff6577', xx=x(i);
    const wick=document.createElementNS('http://www.w3.org/2000/svg','line');
    wick.setAttribute('x1',xx);wick.setAttribute('x2',xx);wick.setAttribute('y1',y(b.high));wick.setAttribute('y2',y(b.low));
    wick.setAttribute('stroke',color);wick.setAttribute('stroke-width','1');svg.appendChild(wick);
    const rect=document.createElementNS('http://www.w3.org/2000/svg','rect');
    const y1=y(Math.max(b.open,b.close)), y2=y(Math.min(b.open,b.close));
    rect.setAttribute('x',xx-candleW/2);rect.setAttribute('y',y1);rect.setAttribute('width',candleW);
    rect.setAttribute('height',Math.max(1.2,y2-y1));rect.setAttribute('fill',color);rect.setAttribute('rx','1');svg.appendChild(rect);
  });
}

function render(data){
  snapshot=data; const x=data.latest;
  setText('price','$ '+fmt(x.price));setText('barTime',x.bar_time_utc+' · age '+Math.round(x.data_age_seconds)+'s');
  setText('feedState',x.feed_state);setText('regime',x.regime);setText('atrPct',x.atr_pct==null?'—':(x.atr_pct*100).toFixed(3)+'%');
  setText('wave',x.wave.wt1==null?'—':(x.wave.wt1>x.wave.wt2?'BULLISH':'BEARISH'));
  setText('squeeze',x.squeeze.on?'COMPRESSED':(x.squeeze.release?'RELEASE':'OPEN'));
  setText('signal',x.signal);setText('longScore',x.long_score+'/100');setText('shortScore',x.short_score+'/100');
  document.getElementById('longFill').style.width=x.long_score+'%';document.getElementById('shortFill').style.width=x.short_score+'%';
  const pill=document.getElementById('signalPill'); pill.className='pill '+(x.signal==='BUY'?'buy':x.signal==='SELL'?'sell':'flat');
  pill.textContent=x.signal==='BUY'?'PAPER BUY CANDIDATE':x.signal==='SELL'?'PAPER SELL CANDIDATE':'STAY FLAT';
  setText('entry',fmt(x.plan.entry));setText('stop',fmt(x.plan.stop));setText('target',fmt(x.plan.target));setText('rr',x.plan.reward_to_risk==null?'—':'1 : '+x.plan.reward_to_risk.toFixed(2));
  drawChart(data.bars); autoPaperTick(); renderPaper();
}

async function load(){
  document.body.classList.add('loading');setText('error','');
  try{
    const r=await fetch('/api/gold?interval='+tf+'&range=1d',{cache:'no-store'});
    if(!r.ok) throw new Error(await r.text());
    render(await r.json());
  }catch(e){setText('error','Feed error: '+e.message)}
  finally{document.body.classList.remove('loading')}
}

async function loadBacktest(){
  try{
    const r=await fetch('/api/backtest?interval=5m&range=5d&spread=0.20&slippage=0.05',{cache:'no-store'});
    if(!r.ok) throw new Error(await r.text());
    const d=await r.json(), s=d.summary;
    setText('btTrades',Math.round(s.trades||0));setText('btWin',((s.win_rate||0)*100).toFixed(1)+'%');
    setText('btPf',s.profit_factor===null?'—':Number(s.profit_factor).toFixed(2));setText('btNet',fmt(s.net_pnl||0));setText('btDd',fmt(s.max_drawdown||0));
  }catch(e){console.warn('backtest',e)}
}

document.querySelectorAll('.tf').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.tf').forEach(x=>x.classList.remove('active'));b.classList.add('active');tf=b.dataset.tf;load();
}));
setInterval(()=>setText('clock',new Date().toLocaleTimeString()),1000);
load();loadBacktest();renderPaper();
setInterval(load,15000);setInterval(loadBacktest,5*60*1000);
</script>
</body>
</html>"""


CAPITAL_OS_HTML = (ROOT / "web" / "capital_os.html").read_text(encoding="utf-8")
MARKET_INTELLIGENCE_HTML = (ROOT / "web" / "market_intelligence.html").read_text(encoding="utf-8")
LEARNING_HTML = (ROOT / "web" / "learning.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
async def capital_os():
    return HTMLResponse(CAPITAL_OS_HTML)


@app.get("/intelligence", response_class=HTMLResponse)
async def intelligence_dashboard():
    return HTMLResponse(MARKET_INTELLIGENCE_HTML)


@app.get("/learning", response_class=HTMLResponse)
async def learning_dashboard():
    return HTMLResponse(LEARNING_HTML)


@app.get("/gold", response_class=HTMLResponse)
async def gold_dashboard():
    return HTMLResponse(DASHBOARD_HTML)
