from __future__ import annotations

import numpy as np
import pandas as pd


def bootstrap_mean_ci(
    pnl: pd.Series | np.ndarray,
    n_boot: int = 10_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> dict[str, float]:
    values = np.asarray(pd.Series(pnl).dropna(), dtype=float)
    if len(values) == 0:
        raise ValueError("At least one P&L observation is required")

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_boot, len(values)))
    means = values[idx].mean(axis=1)

    alpha = (1 - confidence) / 2
    lo, hi = np.quantile(means, [alpha, 1 - alpha])

    return {
        "mean": float(values.mean()),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "prob_mean_positive": float((means > 0).mean()),
    }


def bootstrap_horizon(
    pnl: pd.Series | np.ndarray,
    horizon: int = 50,
    n_paths: int = 5_000,
    seed: int = 42,
) -> dict[str, float]:
    values = np.asarray(pd.Series(pnl).dropna(), dtype=float)
    if len(values) == 0:
        raise ValueError("At least one P&L observation is required")
    if horizon < 1:
        raise ValueError("horizon must be >= 1")

    rng = np.random.default_rng(seed)
    paths = rng.choice(values, size=(n_paths, horizon), replace=True)
    cumulative = paths.cumsum(axis=1)
    terminal = cumulative[:, -1]

    with_origin = np.concatenate([np.zeros((n_paths, 1)), cumulative], axis=1)
    peaks = np.maximum.accumulate(with_origin, axis=1)
    max_dd = -(with_origin - peaks).min(axis=1)

    q05, q50, q95 = np.quantile(terminal, [0.05, 0.5, 0.95])
    return {
        "horizon": int(horizon),
        "terminal_p05": float(q05),
        "terminal_median": float(q50),
        "terminal_p95": float(q95),
        "prob_terminal_loss": float((terminal < 0).mean()),
        "median_max_drawdown": float(np.median(max_dd)),
        "max_drawdown_p95": float(np.quantile(max_dd, 0.95)),
    }
