from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .costs import CostModel
from .strategy import ScalpingConfig, generate_signals


@dataclass(frozen=True)
class BacktestConfig:
    starting_cash: float = 100_000.0
    quantity: float = 1.0
    stop_atr: float = 1.5
    target_atr: float = 2.0
    max_holding_bars: int = 20


def run_backtest(
    bars: pd.DataFrame,
    *,
    strategy: ScalpingConfig | None = None,
    backtest: BacktestConfig | None = None,
    costs: CostModel | None = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Simple next-bar-entry backtest.

    Signals are computed on the completed bar and entry occurs at next bar open
    to reduce look-ahead bias. Intrabar stop/target conflicts are resolved
    conservatively in favor of the stop.
    """
    s = strategy or ScalpingConfig()
    b = backtest or BacktestConfig()
    cost = costs or CostModel()

    x = generate_signals(bars, s).copy()
    trades: list[dict] = []
    position = None

    for i in range(1, len(x)):
        row = x.iloc[i]
        prev = x.iloc[i - 1]

        if position is None:
            signal = prev["signal"]
            atr_value = prev["atr"]
            if signal not in {"BUY", "SELL"} or pd.isna(atr_value):
                continue

            raw_entry = float(row["open"])
            entry = cost.entry_price(raw_entry, signal)
            if signal == "BUY":
                stop = entry - b.stop_atr * float(atr_value)
                target = entry + b.target_atr * float(atr_value)
            else:
                stop = entry + b.stop_atr * float(atr_value)
                target = entry - b.target_atr * float(atr_value)

            position = {
                "side": signal,
                "entry_i": i,
                "entry_time": x.index[i],
                "entry": entry,
                "stop": stop,
                "target": target,
                "quantity": b.quantity,
            }
            continue

        side = position["side"]
        held = i - position["entry_i"]
        high = float(row["high"])
        low = float(row["low"])
        reason = None
        raw_exit = None

        if side == "BUY":
            stop_hit = low <= position["stop"]
            target_hit = high >= position["target"]
            if stop_hit:
                raw_exit, reason = position["stop"], "STOP"
            elif target_hit:
                raw_exit, reason = position["target"], "TARGET"
        else:
            stop_hit = high >= position["stop"]
            target_hit = low <= position["target"]
            if stop_hit:
                raw_exit, reason = position["stop"], "STOP"
            elif target_hit:
                raw_exit, reason = position["target"], "TARGET"

        if reason is None and held >= b.max_holding_bars:
            raw_exit, reason = float(row["close"]), "TIME"

        if reason is None:
            continue

        exit_price = cost.exit_price(float(raw_exit), side)
        direction = 1.0 if side == "BUY" else -1.0
        gross = (
            direction
            * (exit_price - position["entry"])
            * position["quantity"]
        )
        commission = cost.commission(position["quantity"])
        net = gross - commission

        trades.append(
            {
                "side": side,
                "entry_time": position["entry_time"],
                "exit_time": x.index[i],
                "entry_price": position["entry"],
                "exit_price": exit_price,
                "quantity": position["quantity"],
                "bars_held": held,
                "exit_reason": reason,
                "net_pnl": net,
            }
        )
        position = None

    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        return trades_df, {
            "trades": 0.0,
            "net_pnl": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
        }

    pnl = trades_df["net_pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(abs(losses.sum()))
    profit_factor = gross_profit / gross_loss if gross_loss else float("inf")

    equity = b.starting_cash + pnl.cumsum()
    peak = equity.cummax()
    drawdown = peak - equity

    summary = {
        "trades": float(len(trades_df)),
        "net_pnl": float(pnl.sum()),
        "win_rate": float((pnl > 0).mean()),
        "avg_trade": float(pnl.mean()),
        "profit_factor": float(profit_factor),
        "max_drawdown": float(drawdown.max()),
        "ending_equity": float(equity.iloc[-1]),
    }
    return trades_df, summary
