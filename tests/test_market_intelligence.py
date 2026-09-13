import pandas as pd

from trading_for_money.intelligence import (
    LEARNING_PATH,
    build_market_regime,
    compute_asset_metrics,
    find_sources,
)


def _frame(start: float, step: float, n: int = 80):
    idx = pd.date_range("2026-01-01", periods=n, freq="D", tz="UTC")
    close = pd.Series([start + step * i for i in range(n)], index=idx)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1000,
        },
        index=idx,
    )


def test_compute_asset_metrics_detects_uptrend():
    out = compute_asset_metrics(_frame(100, 1), symbol="SPY", label="S&P 500")
    assert out["trend"] == "up"
    assert out["return_20d"] > 0
    assert out["ma20"] > out["ma50"]


def test_market_regime_can_be_risk_on():
    metrics = [
        {"symbol": "SPY", "return_20d": 0.05, "group": "benchmark"},
        {"symbol": "QQQ", "return_20d": 0.09, "group": "growth"},
        {"symbol": "IWM", "return_20d": 0.03, "group": "small_caps"},
        {"symbol": "XLY", "return_20d": 0.06, "group": "sector", "label": "Consumer Discretionary"},
        {"symbol": "XLP", "return_20d": 0.01, "group": "sector", "label": "Consumer Staples"},
        {"symbol": "XLK", "return_20d": 0.08, "group": "sector", "label": "Technology"},
        {"symbol": "TLT", "return_20d": 0.00, "group": "rates"},
    ]
    regime = build_market_regime(metrics)
    assert regime["regime"] == "RISK_ON"
    assert regime["risk_score"] >= 2


def test_source_finder_prioritizes_sec_for_10q():
    sources = find_sources("10-Q earnings company")
    assert sources[0]["key"] == "sec_edgar"


def test_learning_path_is_free_and_ordered():
    assert len(LEARNING_PATH) >= 8
    assert all(x["free"] for x in LEARNING_PATH)
    assert [x["sequence"] for x in LEARNING_PATH] == sorted(
        x["sequence"] for x in LEARNING_PATH
    )
