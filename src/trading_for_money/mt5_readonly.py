from __future__ import annotations

import pandas as pd


class MetaTraderReadOnly:
    """Read-only adapter for MetaTrader 5.

    Deliberately does NOT expose order_send or any write/execution method.
    """

    def __init__(self):
        self.mt5 = None

    def connect(self) -> None:
        import MetaTrader5 as mt5

        if not mt5.initialize():
            raise RuntimeError(f"MetaTrader5 initialize failed: {mt5.last_error()}")
        self.mt5 = mt5

    def close(self) -> None:
        if self.mt5 is not None:
            self.mt5.shutdown()
            self.mt5 = None

    def account_info(self) -> dict:
        self._ensure()
        info = self.mt5.account_info()
        if info is None:
            raise RuntimeError(f"account_info failed: {self.mt5.last_error()}")
        return info._asdict()

    def positions(self) -> pd.DataFrame:
        self._ensure()
        values = self.mt5.positions_get()
        if values is None:
            raise RuntimeError(f"positions_get failed: {self.mt5.last_error()}")
        return pd.DataFrame([x._asdict() for x in values])

    def ticks(self, symbol: str) -> dict:
        self._ensure()
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"symbol_info_tick failed: {self.mt5.last_error()}")
        return tick._asdict()

    def bars(self, symbol: str, timeframe, count: int = 500) -> pd.DataFrame:
        self._ensure()
        rates = self.mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            raise RuntimeError(f"copy_rates_from_pos failed: {self.mt5.last_error()}")
        frame = pd.DataFrame(rates)
        if not frame.empty:
            frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
        return frame

    def _ensure(self) -> None:
        if self.mt5 is None:
            raise RuntimeError("Call connect() first.")
