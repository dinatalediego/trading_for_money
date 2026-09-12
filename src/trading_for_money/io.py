from __future__ import annotations

from pathlib import Path
from typing import IO

import pandas as pd

REQUIRED_TRADE_COLUMNS = {
    "trade_id",
    "closed_at",
    "symbol",
    "side",
    "volume",
    "entry_price",
    "exit_price",
    "pnl",
}


def normalize_trades(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_TRADE_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = df.copy()
    out["closed_at"] = pd.to_datetime(out["closed_at"], errors="coerce")
    if out["closed_at"].isna().any():
        raise ValueError("closed_at contains invalid datetimes")

    out["side"] = out["side"].astype(str).str.lower().str.strip()
    invalid_side = ~out["side"].isin(["buy", "sell"])
    if invalid_side.any():
        values = sorted(out.loc[invalid_side, "side"].unique().tolist())
        raise ValueError(f"side must be buy/sell. Invalid values: {values}")

    numeric = ["volume", "entry_price", "exit_price", "pnl"]
    for col in numeric:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        if out[col].isna().any():
            raise ValueError(f"{col} contains non-numeric values")

    if out["trade_id"].duplicated().any():
        raise ValueError("trade_id must be unique")

    return out.sort_values("closed_at").reset_index(drop=True)


def load_trades(source: str | Path | IO[bytes]) -> pd.DataFrame:
    return normalize_trades(pd.read_csv(source))


def load_account_events(source: str | Path | IO[bytes]) -> pd.DataFrame:
    events = pd.read_csv(source).copy()
    required = {"event_id", "event_at", "event_type", "amount"}
    missing = required.difference(events.columns)
    if missing:
        raise ValueError(f"Missing event columns: {sorted(missing)}")
    events["event_at"] = pd.to_datetime(events["event_at"], errors="coerce")
    events["amount"] = pd.to_numeric(events["amount"], errors="coerce")
    if events[["event_at", "amount"]].isna().any().any():
        raise ValueError("account events contain invalid date/amount values")
    return events.sort_values("event_at").reset_index(drop=True)
