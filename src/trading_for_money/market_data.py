from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


DEFAULT_UNIVERSE = {
    "SPY": "US large-cap market",
    "QQQ": "Nasdaq / growth proxy",
    "IWM": "US small caps",
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLV": "Health care",
    "XLY": "Consumer discretionary",
    "XLP": "Consumer staples",
    "GLD": "Gold",
    "TLT": "Long-duration US Treasuries",
}


@dataclass(frozen=True)
class MarketUniverse:
    symbols: tuple[str, ...]

    @classmethod
    def default(cls) -> "MarketUniverse":
        return cls(tuple(DEFAULT_UNIVERSE.keys()))


def download_prices(
    symbols: Iterable[str] | None = None,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Download adjusted close prices with yfinance.

    This is intended for research/paper-trading only. Data quality and delay
    depend on the upstream provider.
    """
    import yfinance as yf

    symbols = tuple(symbols or MarketUniverse.default().symbols)
    raw = yf.download(
        list(symbols),
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True,
    )

    if raw.empty:
        raise ValueError("No market data returned.")

    if len(symbols) == 1:
        close = raw[["Close"]].rename(columns={"Close": symbols[0]})
    else:
        close = raw["Close"].copy()

    close = close.dropna(how="all").sort_index()
    return close
