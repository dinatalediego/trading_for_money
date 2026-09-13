from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app


client = TestClient(app.app)


def test_portfolio_health_api_is_advisory(monkeypatch):
    async def fake_benchmark(symbol: str, window_days: int):
        assert symbol == "SPY"
        return 0.06, 650.0, None

    monkeypatch.setattr(app, "benchmark_context", fake_benchmark)

    response = client.post(
        "/api/portfolio-health",
        json={
            "positions": [
                {
                    "symbol": "CORE",
                    "bucket": "CORE",
                    "quantity": 1,
                    "market_price": 7000,
                    "avg_cost": 6500,
                    "asset_class": "etf",
                },
                {
                    "symbol": "OPP",
                    "bucket": "OPPORTUNITY",
                    "quantity": 1,
                    "market_price": 1500,
                    "avg_cost": 1400,
                    "asset_class": "equity",
                },
                {
                    "symbol": "CASH",
                    "bucket": "CASH",
                    "quantity": 1,
                    "market_price": 1000,
                    "avg_cost": 1000,
                    "asset_class": "cash",
                },
                {
                    "symbol": "GLD",
                    "bucket": "GOLD_LAB",
                    "quantity": 1,
                    "market_price": 500,
                    "avg_cost": 480,
                    "asset_class": "commodity",
                },
            ],
            "target_weights": {
                "CORE": 0.70,
                "OPPORTUNITY": 0.15,
                "GOLD_LAB": 0.05,
                "CASH": 0.10,
            },
            "monthly_contribution": 200,
            "constitution": {
                "emergency_fund_ready": True,
                "max_single_position_pct": 0.75,
                "benchmark_symbol": "SPY",
                "benchmark_window_days": 60,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["health_status"] == "STRONG"
    assert data["benchmark_return"] == 0.06
    assert data["diagnostics"]["benchmark_comparison_kind"] == "context_only"
    assert "create no broker order" in data["diagnostics"]["non_execution_notice"]
