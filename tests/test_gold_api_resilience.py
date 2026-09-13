from pathlib import Path
import sys

import numpy as np
import pandas as pd
from fastapi import HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app


client = TestClient(app.app)


def _bars(n=120):
    idx = pd.date_range("2026-09-11 18:00", periods=n, freq="min", tz="UTC")
    base = np.linspace(4380, 4410, n)
    wave = np.sin(np.linspace(0, 8, n))
    close = base + wave
    return pd.DataFrame(
        {
            "open": close - 0.3,
            "high": close + 0.8,
            "low": close - 0.8,
            "close": close,
            "volume": np.full(n, 1000),
        },
        index=idx,
    )


def test_gold_1d_falls_back_to_5d_when_provider_has_no_bars(monkeypatch):
    calls = []

    async def fake_fetch(symbol=app.GOLD_RESEARCH_SYMBOL, *, interval="1m", range_="1d"):
        calls.append(range_)
        if range_ == "1d":
            raise HTTPException(status_code=502, detail="market data provider returned no bars")
        return _bars(), {"currency": "USD", "exchangeName": "CMX"}

    monkeypatch.setattr(app, "fetch_ohlcv", fake_fetch)

    response = client.get("/api/gold?interval=1m&range=1d")
    assert response.status_code == 200
    data = response.json()
    assert calls == ["1d", "5d"]
    assert data["fallback_used"] is True
    assert data["effective_range"] == "5d"
    assert data["latest"]["feed_state"] == "STALE_OR_MARKET_CLOSED"
    assert len(data["bars"]) > 0
