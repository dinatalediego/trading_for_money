import pandas as pd

from trading_for_money.scalping.costs import CostModel
from trading_for_money.scalping.risk import (
    RiskPolicy,
    RiskState,
    evaluate_risk_gate,
)
from trading_for_money.scalping.strategy import generate_signals


def _bars(n=120):
    idx = pd.date_range("2026-01-01", periods=n, freq="min")
    close = pd.Series([100 + i * 0.05 for i in range(n)], index=idx)
    return pd.DataFrame(
        {
            "open": close.shift(1).fillna(close.iloc[0]),
            "high": close + 0.10,
            "low": close - 0.10,
            "close": close,
            "volume": 1000,
        },
        index=idx,
    )


def test_signal_engine_returns_scores():
    out = generate_signals(_bars())
    assert {"long_score", "short_score", "signal", "atr"}.issubset(out.columns)
    assert out["signal"].isin(["BUY", "SELL", "FLAT"]).all()


def test_cost_model_penalizes_round_trip():
    model = CostModel(spread=0.20, slippage_per_side=0.05)
    entry = model.entry_price(100.0, "BUY")
    exit_ = model.exit_price(100.0, "BUY")
    assert entry > 100.0
    assert exit_ < 100.0


def test_risk_gate_blocks_large_spread():
    d = evaluate_risk_gate(
        RiskPolicy(max_spread_to_atr=0.20),
        RiskState(start_day_equity=1000, current_equity=1000),
        atr_value=1.0,
        spread=0.30,
        reward_to_risk=2.0,
    )
    assert not d.allowed
