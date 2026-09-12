from __future__ import annotations

import numpy as np
import pandas as pd

from .agent_models import MarketInsight


def _trend(ret: float, threshold: float = 0.01) -> str:
    if ret > threshold:
        return "up"
    if ret < -threshold:
        return "down"
    return "flat"


def _strength(rel20: float, ret60: float) -> str:
    score = int(rel20 > 0.02) + int(ret60 > 0.05)
    if score == 2:
        return "strong"
    if score == 1:
        return "moderate"
    return "weak"


def build_market_insights(
    prices: pd.DataFrame,
    benchmark: str = "SPY",
    labels: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Create a cross-sectional regime table from price history."""
    if benchmark not in prices.columns:
        raise ValueError(f"Benchmark {benchmark!r} is not present in prices.")
    if len(prices) < 65:
        raise ValueError("At least 65 observations are required.")

    labels = labels or {}
    returns = prices.pct_change()

    rows = []
    bench20 = prices[benchmark].iloc[-1] / prices[benchmark].iloc[-21] - 1

    for symbol in prices.columns:
        series = prices[symbol].dropna()
        if len(series) < 65:
            continue

        r20 = series.iloc[-1] / series.iloc[-21] - 1
        r60 = series.iloc[-1] / series.iloc[-61] - 1
        rel20 = r20 - bench20
        vol20 = returns[symbol].tail(20).std(ddof=1) * np.sqrt(252)

        insight = MarketInsight(
            symbol=symbol,
            label=labels.get(symbol, symbol),
            trend_20d=_trend(float(r20)),
            trend_60d=_trend(float(r60)),
            return_20d=float(r20),
            return_60d=float(r60),
            rel_20d_vs_spy=float(rel20),
            vol_20d_annualized=float(vol20),
            strength=_strength(float(rel20), float(r60)),
            explanation=(
                f"{symbol}: 20d={r20:+.1%}, 60d={r60:+.1%}, "
                f"relative 20d vs {benchmark}={rel20:+.1%}, "
                f"annualized vol≈{vol20:.1%}."
            ),
        )
        rows.append(insight.to_dict())

    out = pd.DataFrame(rows)
    return out.sort_values(
        ["rel_20d_vs_spy", "return_60d"],
        ascending=False,
    ).reset_index(drop=True)


def market_narrative(insights: pd.DataFrame) -> list[str]:
    """Turn the regime table into concise, deterministic observations."""
    if insights.empty:
        return ["No insights available."]

    notes: list[str] = []
    ranked = insights.sort_values("rel_20d_vs_spy", ascending=False)
    top = ranked.iloc[0]
    bottom = ranked.iloc[-1]

    notes.append(
        f"Leadership: {top['label']} ({top['symbol']}) has the strongest "
        f"20-day relative performance vs SPY at {top['rel_20d_vs_spy']:+.1%}."
    )
    notes.append(
        f"Laggard: {bottom['label']} ({bottom['symbol']}) has the weakest "
        f"20-day relative performance vs SPY at {bottom['rel_20d_vs_spy']:+.1%}."
    )

    tech = insights.loc[insights["symbol"] == "XLK"]
    small = insights.loc[insights["symbol"] == "IWM"]
    if not tech.empty and not small.empty:
        spread = float(tech.iloc[0]["return_20d"] - small.iloc[0]["return_20d"])
        if spread > 0.03:
            notes.append(
                "Large-cap technology is materially outperforming small caps over "
                f"20 sessions by about {spread:.1%}; leadership is concentrated rather "
                "than broad."
            )
        elif spread < -0.03:
            notes.append(
                "Small caps are materially outperforming technology over 20 sessions "
                f"by about {-spread:.1%}; participation appears broader/cyclical."
            )

    gold = insights.loc[insights["symbol"] == "GLD"]
    bonds = insights.loc[insights["symbol"] == "TLT"]
    if not gold.empty and not bonds.empty:
        notes.append(
            "Cross-asset check: GLD 20d "
            f"{float(gold.iloc[0]['return_20d']):+.1%}; TLT 20d "
            f"{float(bonds.iloc[0]['return_20d']):+.1%}."
        )

    return notes
