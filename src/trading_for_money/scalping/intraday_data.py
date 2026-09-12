from __future__ import annotations

import pandas as pd


def download_intraday_ohlcv(
    symbol: str,
    *,
    period: str = "5d",
    interval: str = "5m",
) -> pd.DataFrame:
    """Download intraday OHLCV for research via yfinance.

    This is not an execution-grade real-time feed. Production/shadow mode should
    replace this adapter with broker-native streaming data.
    """
    import yfinance as yf

    raw = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if raw.empty:
        raise ValueError(f"No intraday data returned for {symbol}")

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    mapping = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    out = raw.rename(columns=mapping)
    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"Missing OHLC fields from provider: {missing}")

    keep = [c for c in ["open", "high", "low", "close", "volume"] if c in out.columns]
    return out[keep].dropna(subset=required).sort_index()
