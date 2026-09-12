from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PaperPosition:
    symbol: str
    quantity: float
    entry_price: float
    opened_at: str


@dataclass
class PaperFill:
    symbol: str
    side: str
    quantity: float
    price: float
    filled_at: str


@dataclass
class PaperBroker:
    cash: float = 100_000.0
    positions: dict[str, PaperPosition] = field(default_factory=dict)
    fills: list[PaperFill] = field(default_factory=list)

    def buy(self, symbol: str, quantity: float, price: float) -> PaperFill:
        if quantity <= 0 or price <= 0:
            raise ValueError("quantity and price must be positive")
        cost = quantity * price
        if cost > self.cash:
            raise ValueError("insufficient paper cash")
        if symbol in self.positions:
            raise ValueError("v0 supports one paper position per symbol")

        now = datetime.now(timezone.utc).isoformat()
        self.cash -= cost
        self.positions[symbol] = PaperPosition(
            symbol=symbol,
            quantity=quantity,
            entry_price=price,
            opened_at=now,
        )
        fill = PaperFill(symbol, "BUY", quantity, price, now)
        self.fills.append(fill)
        return fill

    def sell_to_close(self, symbol: str, price: float) -> PaperFill:
        if symbol not in self.positions:
            raise ValueError("no paper position exists for symbol")
        if price <= 0:
            raise ValueError("price must be positive")

        pos = self.positions.pop(symbol)
        now = datetime.now(timezone.utc).isoformat()
        self.cash += pos.quantity * price
        fill = PaperFill(symbol, "SELL", pos.quantity, price, now)
        self.fills.append(fill)
        return fill

    def equity(self, last_prices: dict[str, float]) -> float:
        marked = sum(
            pos.quantity * last_prices[pos.symbol]
            for pos in self.positions.values()
            if pos.symbol in last_prices
        )
        return self.cash + marked
