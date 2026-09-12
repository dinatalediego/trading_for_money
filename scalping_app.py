from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trading_for_money.scalping.backtest import BacktestConfig, run_backtest
from trading_for_money.scalping.costs import CostModel
from trading_for_money.scalping.intraday_data import download_intraday_ohlcv
from trading_for_money.scalping.strategy import ScalpingConfig, generate_signals

st.set_page_config(page_title="Scalping Research Lab", layout="wide")
st.title("Scalping Research Lab · v0.3")
st.caption(
    "Intraday signal research + cost-aware paper backtesting. "
    "No real-money order routing."
)

PRESETS = {
    "Gold futures proxy (GC=F)": "GC=F",
    "Nasdaq futures proxy (NQ=F)": "NQ=F",
    "Nasdaq 100 ETF proxy (QQQ)": "QQQ",
    "Custom": "",
}

with st.sidebar:
    st.header("Market")
    preset = st.selectbox("Research feed", list(PRESETS))
    symbol = PRESETS[preset]
    if preset == "Custom":
        symbol = st.text_input("Ticker / feed symbol", value="")

    interval = st.selectbox("Bar interval", ["1m", "2m", "5m", "15m"], index=2)
    period_options = ["1d", "5d", "1mo"]
    period = st.selectbox("History", period_options, index=1)

    st.header("Signal engine")
    min_score = st.slider("Minimum confluence score", 50, 100, 70, 5)
    fast = st.number_input("Fast EMA", min_value=2, max_value=100, value=20)
    slow = st.number_input("Slow EMA", min_value=5, max_value=300, value=50)

    st.header("Paper exits")
    stop_atr = st.slider("Stop · ATR", 0.5, 5.0, 1.5, 0.25)
    target_atr = st.slider("Target · ATR", 0.5, 8.0, 2.0, 0.25)
    max_bars = st.slider("Max holding bars", 1, 100, 20)

    st.header("Research costs")
    spread = st.number_input(
        "Assumed spread (price units)", min_value=0.0, value=0.0, step=0.01
    )
    slippage = st.number_input(
        "Slippage per side (price units)", min_value=0.0, value=0.0, step=0.01
    )

if not symbol:
    st.info("Choose a preset or provide a symbol.")
    st.stop()

try:
    bars = download_intraday_ohlcv(symbol, period=period, interval=interval)
except Exception as exc:
    st.error(f"Data provider error: {exc}")
    st.stop()

strategy = ScalpingConfig(
    fast_ema=int(fast),
    slow_ema=int(slow),
    min_score=int(min_score),
)
signals = generate_signals(bars, strategy)

latest = signals.iloc[-1]
latest_signal = latest["signal"]
display_signal = {
    "BUY": "PAPER BUY CANDIDATE",
    "SELL": "PAPER SELL CANDIDATE",
    "FLAT": "STAY FLAT",
}[latest_signal]

st.subheader(f"{symbol} · latest completed bar")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Research state", display_signal)
c2.metric("Close", f"{float(latest['close']):,.2f}")
c3.metric("Long score", f"{int(latest['long_score'])}/100")
c4.metric("Short score", f"{int(latest['short_score'])}/100")
atr_pct = float(latest["atr_pct"]) if pd.notna(latest["atr_pct"]) else float("nan")
c5.metric("ATR / price", "" if pd.isna(atr_pct) else f"{atr_pct:.2%}")

st.subheader("Market chart")
chart = signals[["close", "ema_fast", "ema_slow"]].dropna()
st.line_chart(chart)

st.subheader("Signal diagnostics")
diag_cols = [
    "close",
    "ema_fast",
    "ema_slow",
    "atr",
    "atr_trend",
    "break_up",
    "break_down",
    "wt1",
    "wt2",
    "squeeze_on",
    "squeeze_release",
    "squeeze_momentum",
    "long_score",
    "short_score",
    "signal",
    "signal_reason",
]
st.dataframe(
    signals[diag_cols].tail(50).iloc[::-1],
    use_container_width=True,
)

st.subheader("Cost-aware paper backtest")
trades, summary = run_backtest(
    bars,
    strategy=strategy,
    backtest=BacktestConfig(
        stop_atr=float(stop_atr),
        target_atr=float(target_atr),
        max_holding_bars=int(max_bars),
    ),
    costs=CostModel(
        spread=float(spread),
        slippage_per_side=float(slippage),
    ),
)

b1, b2, b3, b4, b5 = st.columns(5)
b1.metric("Trades", int(summary.get("trades", 0)))
b2.metric("Win rate", f"{summary.get('win_rate', 0):.1%}")
b3.metric("Net P&L*", f"{summary.get('net_pnl', 0):+.2f}")
pf = summary.get("profit_factor", 0)
b4.metric("Profit factor", "∞" if pf == float("inf") else f"{pf:.2f}")
b5.metric("Max drawdown*", f"{summary.get('max_drawdown', 0):.2f}")

st.caption(
    "*Research units depend on the instrument/contract. Enter realistic spread, "
    "slippage and later commission/contract metadata before interpreting results."
)

if not trades.empty:
    trades = trades.copy()
    trades["cumulative_pnl"] = trades["net_pnl"].cumsum()
    st.line_chart(trades.set_index("exit_time")["cumulative_pnl"])
    st.dataframe(trades.tail(100).iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.info("No paper trades were produced by the current parameters.")

st.warning(
    "High win rate is not the optimization target. A strategy is only interesting "
    "if net expectancy remains positive after realistic costs and on unseen periods."
)
