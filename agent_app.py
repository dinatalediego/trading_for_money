from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trading_for_money.market_data import DEFAULT_UNIVERSE, download_prices
from trading_for_money.market_insights import build_market_insights, market_narrative
from trading_for_money.paper_agent import relative_strength_proposals

st.set_page_config(page_title="Agentic Market Lab", layout="wide")
st.title("Agentic Market Lab · v0.2")
st.caption(
    "Observa liderazgo, regímenes y tendencias; genera propuestas reproducibles "
    "solo para paper trading."
)

period = st.sidebar.selectbox("Ventana de datos", ["6mo", "1y", "2y"], index=1)

with st.spinner("Descargando datos de mercado..."):
    prices = download_prices(period=period)
    insights = build_market_insights(prices, labels=DEFAULT_UNIVERSE)

st.subheader("Market regime")
for note in market_narrative(insights):
    st.write("•", note)

c1, c2 = st.columns([2, 1])
with c1:
    st.markdown("**Relative strength / leadership**")
    display = insights[
        [
            "symbol",
            "label",
            "trend_20d",
            "trend_60d",
            "return_20d",
            "return_60d",
            "rel_20d_vs_spy",
            "vol_20d_annualized",
            "strength",
        ]
    ].copy()
    for col in [
        "return_20d",
        "return_60d",
        "rel_20d_vs_spy",
        "vol_20d_annualized",
    ]:
        display[col] = display[col].map(lambda x: f"{x:.1%}")
    st.dataframe(display, use_container_width=True, hide_index=True)

with c2:
    st.markdown("**20-day performance**")
    chart = insights.set_index("symbol")["return_20d"].sort_values()
    st.bar_chart(chart)

st.subheader("Paper proposals")
st.caption(
    "Estas propuestas son experimentos reproducibles; no se envían órdenes reales."
)
proposals = relative_strength_proposals(insights)
rows = [p.to_dict() for p in proposals]
st.dataframe(rows, use_container_width=True, hide_index=True)

st.subheader("What the agent is learning")
st.markdown(
    """
- ¿Qué sectores mantienen liderazgo fuera de muestra?
- ¿Cuándo el liderazgo se concentra vs. se amplía?
- ¿Qué señales sobreviven costos y cambios de régimen?
- ¿Las decisiones humanas mejoran o empeoran las propuestas sistemáticas?
- ¿Qué confianza debería asignarse a cada tipo de insight?
"""
)
