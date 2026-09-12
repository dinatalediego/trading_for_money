# Data contract

## trades.csv

Cada fila representa una operación cerrada.

| columna | tipo | descripción |
|---|---|---|
| trade_id | text | identificador estable |
| closed_at | datetime | fecha/hora de cierre mostrada por el broker |
| symbol | text | instrumento, por ejemplo XAUUSD.f |
| side | text | buy / sell |
| volume | float | volumen reportado por el broker |
| entry_price | float | precio de entrada |
| exit_price | float | precio de salida |
| pnl | float | resultado monetario neto reportado para la operación |
| source | text | mt5_export, screenshot, manual, etc. |
| notes | text | comentario libre |

Campos recomendados para la siguiente versión: `opened_at`, `commission`, `swap`, `sl`, `tp`, `balance_before`, `risk_amount`, `setup`, `reason_entry`, `reason_exit`, `emotion`.

## account_events.csv

Movimientos no representados como trades: fees, deducciones, depósitos, retiros o ajustes.

`amount` debe llevar signo: costo = negativo; abono = positivo.

## Privacidad

Coloca exports reales en `data/private/` o `data/raw/`; ambas rutas están ignoradas por Git para evitar publicar información de cuenta accidentalmente.
