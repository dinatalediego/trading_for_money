from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trading_for_money.diagnostics import bootstrap_horizon, bootstrap_mean_ci
from trading_for_money.io import load_account_events, load_trades
from trading_for_money.metrics import (
    net_after_account_events,
    pnl_by_hour,
    pnl_by_side,
    summary_metrics,
)

st.set_page_config(page_title="Trading for Money — Evidence Lab", layout="wide")
st.title("Trading for Money · Evidence Lab")
st.caption(
    "Convierte trades manuales en evidencia: rendimiento, incertidumbre, costos y riesgo."
)

st.sidebar.header("Datos")
uploaded = st.sidebar.file_uploader("Sube trades.csv", type=["csv"])
events_uploaded = st.sidebar.file_uploader("Sube account_events.csv", type=["csv"])

try:
    trades = load_trades(uploaded if uploaded else ROOT / "data/sample_trades.csv")
    if events_uploaded:
        events = load_account_events(events_uploaded)
    elif uploaded:
        events = pd.DataFrame(columns=["event_id", "event_at", "event_type", "amount"])
    else:
        events = load_account_events(ROOT / "data/sample_account_events.csv")
except ValueError as exc:
    st.error(str(exc))
    st.stop()

metrics = summary_metrics(trades)
net_total = net_after_account_events(trades, events)

st.subheader("1 · Reality check")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Trades", metrics["trades"])
c2.metric("Win rate", f'{metrics["win_rate"]:.1%}')
c3.metric("P&L trades", f'{metrics["net_trade_pnl"]:+.2f}')
c4.metric("P&L + eventos", f"{net_total:+.2f}")
c5.metric("Max drawdown", f'{metrics["max_drawdown"]:.2f}')

c6, c7, c8, c9 = st.columns(4)
pf = metrics["profit_factor"]
c6.metric("Profit factor", "∞" if pf == float("inf") else f"{pf:.2f}")
c7.metric("Avg trade", f'{metrics["avg_pnl"]:+.2f}')
c8.metric("Avg win", f'{metrics["avg_win"]:+.2f}')
c9.metric("Avg loss", f'-{metrics["avg_loss"]:.2f}' if metrics["avg_loss"] else "0.00")

st.info(
    "Un win rate alto no basta. El objetivo es comprobar si la expectativa sigue siendo "
    "positiva fuera de muestra y después de todos los costos."
)

st.subheader("2 · Curva de P&L")
equity = trades[["closed_at", "pnl"]].copy()
equity["cumulative_pnl"] = equity["pnl"].cumsum()
st.line_chart(equity.set_index("closed_at")["cumulative_pnl"])

left, right = st.columns(2)
with left:
    st.markdown("**Por dirección**")
    side = pnl_by_side(trades)
    st.dataframe(side, use_container_width=True, hide_index=True)
with right:
    st.markdown("**Por hora de cierre**")
    hourly = pnl_by_hour(trades)
    st.dataframe(hourly, use_container_width=True, hide_index=True)

st.subheader("3 · ¿Hay edge o solo una buena racha?")
boot = bootstrap_mean_ci(trades["pnl"])
b1, b2, b3 = st.columns(3)
b1.metric("Expectancy observada", f'{boot["mean"]:+.2f} / trade')
b2.metric(
    "IC bootstrap 95%",
    f'{boot["ci_low"]:+.2f} → {boot["ci_high"]:+.2f}',
)
b3.metric("P(media > 0) bootstrap", f'{boot["prob_mean_positive"]:.1%}')

if boot["ci_low"] <= 0:
    st.warning(
        "Con esta muestra todavía no podemos descartar una expectativa media nula o negativa."
    )
else:
    st.success(
        "La muestra observada es consistente con expectativa positiva, pero falta validación "
        "fuera de muestra y más operaciones."
    )

st.subheader("4 · Stress test empírico")
horizon = st.slider("Horizonte simulado de trades", 10, 200, 50, step=10)
sim = bootstrap_horizon(trades["pnl"], horizon=horizon)
s1, s2, s3, s4 = st.columns(4)
s1.metric("P&L mediano", f'{sim["terminal_median"]:+.2f}')
s2.metric("Escenario P05", f'{sim["terminal_p05"]:+.2f}')
s3.metric("Prob. terminar en pérdida", f'{sim["prob_terminal_loss"]:.1%}')
s4.metric("DD P95", f'{sim["max_drawdown_p95"]:.2f}')

st.caption(
    "El stress test remuestrea los trades observados. No modela cambios de régimen, slippage "
    "extremo ni eventos fuera de la muestra; por eso es un diagnóstico, no un pronóstico."
)

st.subheader("5 · Journal")
display_cols = [
    "closed_at",
    "symbol",
    "side",
    "volume",
    "entry_price",
    "exit_price",
    "pnl",
    "notes",
]
st.dataframe(trades[display_cols], use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown(
    "**Siguiente experimento:** exportar el historial completo de MT5 y etiquetar cada trade "
    "por setup, stop inicial, take profit, motivo de entrada/salida y contexto de mercado. "
    "Con eso podremos medir expectancy en R, no solo en dinero."
)
