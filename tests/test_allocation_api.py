from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app


client = TestClient(app.app)


def test_allocation_api_is_non_executing_and_reconciles():
    response = client.post(
        "/api/allocation",
        json={
            "contribution_amount": 1000,
            "bucket_values": {
                "CORE": 0,
                "OPPORTUNITY": 0,
                "GOLD_LAB": 0,
                "CASH": 0,
            },
            "target_weights": {
                "CORE": 0.70,
                "OPPORTUNITY": 0.15,
                "GOLD_LAB": 0.05,
                "CASH": 0.10,
            },
            "goals": [],
            "gold": {
                "closed_trades": 0,
                "expectancy_r": None,
                "profit_factor": None,
                "max_drawdown_r": 0,
                "worker_healthy": True,
            },
            "opportunity_thesis_coverage": 0,
            "base_currency": "USD",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert round(sum(item["amount"] for item in data["items"]), 2) == 1000
    gold = next(item for item in data["items"] if item["bucket"] == "GOLD_LAB")
    assert gold["amount"] == 0
    assert gold["deployment_mode"] == "RESEARCH_ONLY"
    assert "moves no money" in data["diagnostics"]["non_execution_notice"]
