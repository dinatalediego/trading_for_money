import math

import pandas as pd

from trading_for_money.metrics import (
    max_drawdown_from_pnl,
    net_after_account_events,
    summary_metrics,
)


def test_summary_metrics_basic():
    trades = pd.DataFrame({"pnl": [10.0, -5.0, 15.0]})
    m = summary_metrics(trades)
    assert m["trades"] == 3
    assert m["wins"] == 2
    assert m["losses"] == 1
    assert math.isclose(m["net_trade_pnl"], 20.0)
    assert math.isclose(m["profit_factor"], 5.0)


def test_max_drawdown():
    pnl = pd.Series([10.0, -4.0, -8.0, 5.0])
    assert math.isclose(max_drawdown_from_pnl(pnl), 12.0)


def test_account_events_are_included():
    trades = pd.DataFrame({"pnl": [100.0, -20.0]})
    events = pd.DataFrame({"amount": [-10.0, 5.0]})
    assert math.isclose(net_after_account_events(trades, events), 75.0)
