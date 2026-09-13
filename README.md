# trading_for_money

**Capital OS** es un sistema personal de inversión, aprendizaje y research cuantitativo diseñado para convertir aportes pequeños y recurrentes en un proceso disciplinado de construcción patrimonial.

Rutas principales en producción:

- `/` — Investment Engine + Capital Allocation
- `/health` — Investment Constitution + Portfolio Health + Benchmark & Attribution + Rebalancing Bands
- `/intelligence` — Market Intelligence + Daily Investor Brief + Source Finder
- `/learning` — Learning Mode
- `/gold` — Gold Alpha Lab (paper/research)

> North star: **sobrevivir, aportar consistentemente y permanecer invertido el tiempo suficiente para que el compounding trabaje.** El sistema no ejecuta órdenes reales.

## Dos líneas del proyecto

### 1. Trade Evidence Lab

La captura inicial corresponde a operaciones manuales de un tercero y se conserva únicamente como **dataset educativo de ejemplo** para practicar:

- reconciliación de P&L;
- win rate;
- expectancy;
- profit factor;
- drawdown;
- incertidumbre;
- costos y deducciones.

No representa el historial del propietario del repositorio ni constituye evidencia suficiente de una estrategia rentable.

Ejecutar:

```bash
streamlit run app.py
```

### 2. Agentic Market Lab

El nuevo foco del repositorio es un agente de investigación semiautónomo que:

- observa un universo cross-asset;
- calcula tendencia, volatilidad y relative strength;
- detecta liderazgo/rezago;
- produce narrativas como "tecnología está liderando mientras small caps se rezagan";
- genera propuestas **solo para paper trading**;
- permite comparar posteriormente decisiones sistemáticas vs. decisiones humanas;
- puede conectarse a MetaTrader 5 en modo **read-only**.

Ejecutar:

```bash
pip install -r requirements.txt
streamlit run agent_app.py
```

Para habilitar únicamente la lectura local de MetaTrader 5 en Windows:

```bash
pip install -r requirements-mt5.txt
```

## Arquitectura

```text
Market data
   ↓
Market snapshot
   ↓
Regime / Narrative Engine
   ↓
Research insights
   ↓
Rule engine
   ↓
Paper proposal
   ↓
Risk / approval gate
   ↓
Paper broker
   ↓
Outcomes + learning
```

La arquitectura detallada y la escalera de autonomía están en:

`docs/AGENT_ARCHITECTURE.md`

## Autonomy ladder

- **L0 — Observer:** métricas y dashboards.
- **L1 — Research Agent:** insights explicables.
- **L2 — Supervised Paper Trader:** propuestas que un humano acepta/rechaza.
- **L3 — Autonomous Paper Trader:** ejecución automática exclusivamente en simulación.
- **L4 — Live Read-only Monitor:** observa MetaTrader/MT5, posiciones y mercado, sin órdenes.
- **L5 — Human-executed Live Trading:** el sistema prepara evidencia/checklists y el humano ejecuta por separado.

## Principios

- **Evidence before autonomy.**
- **Paper before live.**
- **Deterministic execution, probabilistic interpretation.**
- **Costs first.**
- **No leakage / walk-forward validation.**
- **No martingale.**
- **No averaging down automático.**
- **Every proposal is auditable.**
- **Uncertainty is a KPI.**

## Estructura

```text
app.py                         # Evidence Lab
agent_app.py                   # Agentic Market Lab

src/trading_for_money/
├── market_data.py             # descarga datos de mercado
├── market_insights.py         # regime / relative-strength engine
├── agent_models.py            # contratos de insights/propuestas
├── paper_agent.py             # estrategia auditable de ejemplo
├── paper_broker.py            # broker simulado
├── mt5_readonly.py            # MetaTrader 5 sin order_send
├── metrics.py
├── diagnostics.py
└── io.py

docs/
├── ROADMAP.md
└── AGENT_ARCHITECTURE.md
```

## Próximo salto

El siguiente nivel útil no es agregar un LLM que "adivine" precios. Es construir un **Market Memory**:

1. snapshot diario de precios/factores;
2. insights producidos;
3. hipótesis;
4. propuesta de paper trade;
5. aprobación/rechazo humano;
6. retorno futuro 1d/5d/20d;
7. MFE/MAE;
8. régimen posterior;
9. evaluación de qué insights realmente agregaron valor.

Así el agente puede aprender qué observaciones funcionan, en qué régimen y con qué grado de confianza.

## Nota

Este repositorio es educativo y de investigación. No garantiza rentabilidad. El código actual no enruta órdenes reales ni expone una función de ejecución live.
