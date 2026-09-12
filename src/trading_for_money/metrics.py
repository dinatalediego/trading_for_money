from __future__ import annotations

import math

import numpy as np
import pandas as pd


def max_drawdown_from_pnl(pnl: pd.Series) -> float:
    values = pd.to_numeric(pnl, errors="coerce").dropna().to_numpy(dtype=float)
    equity = np.concatenate(([0.0], np.cumsum(values)))
    peaks = np.maximum.accumulate(equity)
    drawdown = equity - peaks
    return float(-drawdown.min())


def summary_metrics(trades: pd.DataFrame) -> dict[str, float | int]:
    pnl = pd.to_numeric(trades["pnl"], errors="coerce").dropna()
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]

    gross_profit = float(wins.sum())
    gross_loss = float(abs(losses.sum()))
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(abs(losses.mean())) if len(losses) else 0.0

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = math.inf
    else:
        profit_factor = 0.0

    payoff_ratio = avg_win / avg_loss if avg_loss > 0 else math.inf
    break_even_win_rate = (
        avg_loss / (avg_win + avg_loss) if (avg_win + avg_loss) > 0 else math.nan
    )

    return {
        "trades": int(len(pnl)),
        "wins": int((pnl > 0).sum()),
        "losses": int((pnl < 0).sum()),
        "win_rate": float((pnl > 0).mean()) if len(pnl) else math.nan,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_trade_pnl": float(pnl.sum()),
        "avg_pnl": float(pnl.mean()) if len(pnl) else math.nan,
        "median_pnl": float(pnl.median()) if len(pnl) else math.nan,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff_ratio": float(payoff_ratio),
        "break_even_win_rate": float(break_even_win_rate),
        "profit_factor": float(profit_factor),
        "max_drawdown": max_drawdown_from_pnl(pnl),
    }


def net_after_account_events(
    trades: pd.DataFrame, account_events: pd.DataFrame | None = None
) -> float:
    trade_total = float(pd.to_numeric(trades["pnl"], errors="coerce").fillna(0).sum())
    if account_events is None or account_events.empty:
        return trade_total
    event_total = float(
        pd.to_numeric(account_events["amount"], errors="coerce").fillna(0).sum()
    )
    return trade_total + event_total


def pnl_by_side(trades: pd.DataFrame) -> pd.DataFrame:
    return (
        trades.groupby("side", as_index=False)
        .agg(
            trades=("trade_id", "count"),
            pnl=("pnl", "sum"),
            avg_pnl=("pnl", "mean"),
            win_rate=("pnl", lambda s: float((s > 0).mean())),
        )
        .sort_values("pnl", ascending=False)
        .reset_index(drop=True)
    )


def pnl_by_hour(trades: pd.DataFrame) -> pd.DataFrame:
    frame = trades.copy()
    frame["hour"] = pd.to_datetime(frame["closed_at"]).dt.hour
    return (
        frame.groupby("hour", as_index=False)
        .agg(
            trades=("trade_id", "count"),
            pnl=("pnl", "sum"),
            avg_pnl=("pnl", "mean"),
            win_rate=("pnl", lambda s: float((s > 0).mean())),
        )
        .sort_values("hour")
        .reset_index(drop=True)
    )
