# trading_for_money

Laboratorio de **trading cuantitativo y aprendizaje de ejecución** para convertir operaciones manuales en evidencia medible.

> Objetivo: no buscar una “señal mágica”, sino responder con datos si una forma de operar tiene **ventaja estadística después de costos**, cuánto riesgo asume y bajo qué condiciones funciona o deja de funcionar.

## Punto de partida

El repositorio nace a partir de operaciones manuales en **XAUUSD**. En la captura inicial se observan 11 operaciones cerradas completas con P&L visible:

- 10 ganadoras y 1 perdedora.
- P&L bruto visible: **+440.37**.
- Deducciones PF visibles: **-127.87**.
- Resultado neto visible de esa muestra: **+312.50**.
- Win rate de la muestra: **90.9%**.

Eso es prometedor como dato inicial, pero **no demuestra todavía un edge**: la muestra es pequeña, puede existir selección de periodo, dependencia entre operaciones, costos no visibles y concentración del resultado en pocas operaciones.

## La idea

El proyecto sigue un ciclo:

**Trade → Evidence → Edge → Risk → Experiment → Decision → Learning**

1. **Journal**: normalizar cada operación y cada costo.
2. **Diagnostics**: win rate, expectancy, profit factor, drawdown, distribución, sesgos por lado y hora.
3. **Uncertainty**: bootstrap para estimar qué tan estable es la rentabilidad observada.
4. **Risk Lab**: stress tests y simulaciones antes de arriesgar capital real.
5. **Strategy Lab**: convertir intuiciones manuales en reglas falsables.
6. **Paper Trading**: validar reglas fuera de muestra antes de automatizar.
7. **Live Monitor**: comparar ejecución real vs. estrategia esperada.

## Ejecutar el MVP

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

También puedes correr los tests:

```bash
pytest
```

## Datos

El MVP incluye dos archivos de ejemplo:

- `data/sample_trades.csv`: operaciones completas visibles en la captura inicial.
- `data/sample_account_events.csv`: deducciones/costos visibles.

Para tus datos reales, usa el esquema descrito en `data/README.md`.

## Principios del sistema

- **Costs first**: una estrategia se evalúa neta de comisiones, swaps y deducciones.
- **No leakage**: las reglas se validan fuera de muestra.
- **No martingale por defecto**.
- **No “doblar para recuperar”** como mecanismo de decisión.
- **Paper before live**: una nueva regla pasa primero por backtest y paper trading.
- **Execution ≠ prediction**: una señal buena puede perder dinero por tamaño, spread o disciplina.
- **Uncertainty is a KPI**: no solo medimos retorno; medimos cuánto confiamos en él.

## Próximo nivel

La hoja de ruta está en `docs/ROADMAP.md`. El siguiente salto útil es importar automáticamente el historial completo de MetaTrader/MT5, enriquecerlo con velas de mercado alrededor de cada entrada y reconstruir qué patrón estabas operando realmente.

## Nota

Este repositorio es una herramienta educativa y de investigación. No garantiza rentabilidad ni sustituye asesoría financiera profesional.
