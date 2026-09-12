from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .indicators import build_indicator_frame


@dataclass(frozen=True)
class ScalpingConfig:
    fast_ema: int = 20
    slow_ema: int = 50
    atr_length: int = 14
    atr_mult: float = 2.0
    structure_lookback: int = 20
    min_score: int = 70
    min_atr_pct: float = 0.0005
    max_atr_pct: float = 0.03


def generate_signals(
    bars: pd.DataFrame,
    config: ScalpingConfig | None = None,
) -> pd.DataFrame:
    """Generate BUY/SELL/FLAT research signals from completed bars."""
    c = config or ScalpingConfig()
    x = build_indicator_frame(
        bars,
        fast_ema=c.fast_ema,
        slow_ema=c.slow_ema,
        atr_length=c.atr_length,
        atr_mult=c.atr_mult,
        structure_lookback=c.structure_lookback,
    )

    x["atr_pct"] = x["atr"] / x["close"]

    long_components = pd.DataFrame(index=x.index)
    long_components["trend"] = x["ema_fast"] > x["ema_slow"]
    long_components["trail"] = x["atr_trend"] > 0
    long_components["structure"] = x["break_up"]
    long_components["wave"] = x["wt1"] > x["wt2"]
    long_components["squeeze"] = (
        (x["squeeze_momentum"] > 0) & x["squeeze_momentum_rising"]
    )

    short_components = pd.DataFrame(index=x.index)
    short_components["trend"] = x["ema_fast"] < x["ema_slow"]
    short_components["trail"] = x["atr_trend"] < 0
    short_components["structure"] = x["break_down"]
    short_components["wave"] = x["wt1"] < x["wt2"]
    short_components["squeeze"] = (
        (x["squeeze_momentum"] < 0) & (~x["squeeze_momentum_rising"])
    )

    weights = {
        "trend": 25,
        "trail": 20,
        "structure": 20,
        "wave": 20,
        "squeeze": 15,
    }

    x["long_score"] = sum(
        long_components[name].fillna(False).astype(int) * weight
        for name, weight in weights.items()
    )
    x["short_score"] = sum(
        short_components[name].fillna(False).astype(int) * weight
        for name, weight in weights.items()
    )

    vol_ok = x["atr_pct"].between(c.min_atr_pct, c.max_atr_pct)
    x["signal"] = "FLAT"
    x.loc[vol_ok & (x["long_score"] >= c.min_score), "signal"] = "BUY"
    x.loc[vol_ok & (x["short_score"] >= c.min_score), "signal"] = "SELL"

    both = (x["long_score"] >= c.min_score) & (x["short_score"] >= c.min_score)
    x.loc[both, "signal"] = "FLAT"

    x["signal_reason"] = (
        "L="
        + x["long_score"].astype(str)
        + " S="
        + x["short_score"].astype(str)
        + " ATR%="
        + x["atr_pct"].map(lambda v: "" if pd.isna(v) else f"{v:.3%}")
    )
    return x
