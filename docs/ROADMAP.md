# Roadmap — de operación manual a sistema de decisión

## M0 — Evidence Lab · ahora

**Objetivo:** dejar de evaluar la estrategia por sensación.

Entregables:
- journal estructurado;
- costos separados de trades;
- win rate, expectancy, payoff, profit factor, drawdown;
- bootstrap de incertidumbre;
- stress test empírico;
- dashboard Streamlit;
- tests + CI.

**Gate para avanzar:** historial completo importado y reconciliado contra el balance del broker.

---

## M1 — Execution Forensics

**Pregunta:** ¿qué haces realmente cuando ganas y cuando pierdes?

Añadir:
- hora de entrada y salida;
- duración;
- stop inicial / take profit;
- riesgo monetario;
- resultado en múltiplos R;
- MAE/MFE;
- captura o snapshot del gráfico;
- etiqueta de setup;
- motivo de entrada/salida;
- contexto: tendencia, volatilidad, sesión y noticias.

Outputs:
- edge por setup;
- edge BUY vs SELL;
- edge por sesión/hora;
- sensibilidad a spread/costos;
- concentración de P&L;
- errores de disciplina.

---

## M2 — Market Replay + Backtest

Ingerir velas OHLCV para XAUUSD y reconstruir el contexto de cada trade.

Separar:
1. **regla de señal**;
2. **regla de salida**;
3. **position sizing**;
4. **cost model**.

Validación:
- train / validation / test temporal;
- walk-forward;
- costos conservadores;
- benchmark simple;
- prevención de look-ahead y overfitting.

**Gate:** resultados positivos fuera de muestra, no solo in-sample.

---

## M3 — Paper Trading Engine

El sistema genera decisiones, pero **no envía órdenes reales**.

Registrar cada oportunidad, incluso las que no tomas:
- timestamp;
- features disponibles en ese instante;
- señal;
- decisión humana;
- resultado hipotético;
- resultado real si se ejecutó.

Esto permite medir el costo de:
- ignorar señales buenas;
- tomar señales fuera de regla;
- entrar tarde;
- salir temprano.

**Gate:** estabilidad durante un número predefinido de trades y distintos regímenes.

---

## M4 — Risk & Regime Engine

Construir límites explícitos:
- pérdida diaria/semanal;
- max drawdown tolerado;
- exposición simultánea;
- volatilidad extrema;
- pausas después de secuencias anómalas;
- detector de cambio de régimen.

El motor no busca “recuperar pérdidas”; busca impedir que una mala fase destruya la capacidad de seguir experimentando.

---

## M5 — Live Decision Support

Integración read-only con MetaTrader/MT5:
- historial automático;
- posiciones abiertas;
- precios y spread;
- dashboard en vivo;
- alertas de desviación respecto a reglas.

La ejecución automática queda separada del motor analítico y deshabilitada por defecto.

---

## North Star

No es “% de trades ganados”.

Es:

> **Expectativa neta fuera de muestra por unidad de riesgo, con drawdown compatible con la supervivencia de la estrategia.**

Métricas principales:
- Expectancy en R;
- IC de expectancy;
- Profit Factor neto;
- Max Drawdown;
- Calmar / recovery;
- costo por errores de ejecución;
- performance por régimen;
- estabilidad out-of-sample.
