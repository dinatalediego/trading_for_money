from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_OHLC = {"open", "high", "low", "close"}


def _validate(frame: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_OHLC.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing OHLC columns: {sorted(missing)}")
    out = frame.copy()
    for col in REQUIRED_OHLC.union({"volume"}.intersection(out.columns)):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if out[list(REQUIRED_OHLC)].isna().any().any():
        raise ValueError("OHLC contains invalid numeric values")
    return out


def true_range(frame: pd.DataFrame) -> pd.Series:
    f = _validate(frame)
    prev = f["close"].shift(1)
    return pd.concat(
        [
            f["high"] - f["low"],
            (f["high"] - prev).abs(),
            (f["low"] - prev).abs(),
        ],
        axis=1,
    ).max(axis=1)


def atr(frame: pd.DataFrame, length: int = 14) -> pd.Series:
    tr = true_range(frame)
    return tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def ema(series: pd.Series, length: int) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").ewm(
        span=length, adjust=False, min_periods=length
    ).mean()


def atr_trailing_state(
    frame: pd.DataFrame,
    atr_length: int = 14,
    multiplier: float = 2.0,
) -> pd.DataFrame:
    """ATR trailing trigger inspired by common volatility-stop systems.

    This is an original implementation and is not a copy of a proprietary script.
    """
    f = _validate(frame)
    a = atr(f, atr_length)
    close = f["close"].to_numpy(dtype=float)
    av = a.to_numpy(dtype=float)

    trail = np.full(len(f), np.nan)
    state = np.zeros(len(f), dtype=int)

    for i in range(len(f)):
        if not np.isfinite(av[i]):
            continue
        if i == 0 or not np.isfinite(trail[i - 1]):
            trail[i] = close[i] - multiplier * av[i]
            state[i] = 1
            continue

        prev_trail = trail[i - 1]
        prev_state = state[i - 1] or 1

        if prev_state >= 0:
            candidate = close[i] - multiplier * av[i]
            if close[i] >= prev_trail:
                trail[i] = max(prev_trail, candidate)
                state[i] = 1
            else:
                trail[i] = close[i] + multiplier * av[i]
                state[i] = -1
        else:
            candidate = close[i] + multiplier * av[i]
            if close[i] <= prev_trail:
                trail[i] = min(prev_trail, candidate)
                state[i] = -1
            else:
                trail[i] = close[i] - multiplier * av[i]
                state[i] = 1

    out = pd.DataFrame(index=f.index)
    out["atr_trail"] = trail
    out["atr_trend"] = state
    out["atr_buy_trigger"] = (out["atr_trend"] == 1) & (out["atr_trend"].shift(1) == -1)
    out["atr_sell_trigger"] = (out["atr_trend"] == -1) & (out["atr_trend"].shift(1) == 1)
    return out


def structure_break(
    frame: pd.DataFrame,
    lookback: int = 20,
) -> pd.DataFrame:
    f = _validate(frame)
    prior_high = f["high"].rolling(lookback).max().shift(1)
    prior_low = f["low"].rolling(lookback).min().shift(1)
    out = pd.DataFrame(index=f.index)
    out["prior_high"] = prior_high
    out["prior_low"] = prior_low
    out["break_up"] = f["close"] > prior_high
    out["break_down"] = f["close"] < prior_low
    return out


def wavetrend_style(
    frame: pd.DataFrame,
    channel_length: int = 10,
    average_length: int = 21,
    signal_length: int = 4,
) -> pd.DataFrame:
    """WaveTrend-style oscillator using typical price and normalized deviation."""
    f = _validate(frame)
    ap = (f["high"] + f["low"] + f["close"]) / 3.0
    esa = ema(ap, channel_length)
    dev = ema((ap - esa).abs(), channel_length)
    ci = (ap - esa) / (0.015 * dev.replace(0, np.nan))
    wt1 = ema(ci, average_length)
    wt2 = wt1.rolling(signal_length).mean()

    out = pd.DataFrame(index=f.index)
    out["wt1"] = wt1
    out["wt2"] = wt2
    out["wt_cross_up"] = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1))
    out["wt_cross_down"] = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1))
    return out


def squeeze_state(
    frame: pd.DataFrame,
    length: int = 20,
    bb_mult: float = 2.0,
    kc_mult: float = 1.5,
) -> pd.DataFrame:
    """Bollinger-vs-Keltner squeeze state with momentum proxy."""
    f = _validate(frame)
    close = f["close"]
    basis = close.rolling(length).mean()
    std = close.rolling(length).std(ddof=0)
    upper_bb = basis + bb_mult * std
    lower_bb = basis - bb_mult * std

    a = atr(f, length)
    upper_kc = basis + kc_mult * a
    lower_kc = basis - kc_mult * a

    squeeze_on = (lower_bb > lower_kc) & (upper_bb < upper_kc)
    squeeze_off = (lower_bb < lower_kc) & (upper_bb > upper_kc)

    midpoint = (
        f["high"].rolling(length).max()
        + f["low"].rolling(length).min()
    ) / 2.0
    raw_momentum = close - (midpoint + basis) / 2.0
    momentum = raw_momentum.rolling(5).mean()

    out = pd.DataFrame(index=f.index)
    out["squeeze_on"] = squeeze_on
    out["squeeze_off"] = squeeze_off
    out["squeeze_release"] = (~squeeze_on) & squeeze_on.shift(1).fillna(False)
    out["squeeze_momentum"] = momentum
    out["squeeze_momentum_rising"] = momentum > momentum.shift(1)
    return out


def build_indicator_frame(
    frame: pd.DataFrame,
    fast_ema: int = 20,
    slow_ema: int = 50,
    atr_length: int = 14,
    atr_mult: float = 2.0,
    structure_lookback: int = 20,
) -> pd.DataFrame:
    f = _validate(frame)
    out = f.copy()
    out["ema_fast"] = ema(f["close"], fast_ema)
    out["ema_slow"] = ema(f["close"], slow_ema)
    out["atr"] = atr(f, atr_length)

    for extra in (
        atr_trailing_state(f, atr_length, atr_mult),
        structure_break(f, structure_lookback),
        wavetrend_style(f),
        squeeze_state(f),
    ):
        out = out.join(extra)

    return out
