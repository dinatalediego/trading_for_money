from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    """Simple round-trip cost model for research.

    Values are in price units unless otherwise noted.
    """

    spread: float = 0.0
    slippage_per_side: float = 0.0
    commission_per_unit_round_trip: float = 0.0

    def entry_price(self, mid: float, side: str) -> float:
        half = self.spread / 2.0
        slip = self.slippage_per_side
        if side.upper() == "BUY":
            return mid + half + slip
        if side.upper() == "SELL":
            return mid - half - slip
        raise ValueError("side must be BUY or SELL")

    def exit_price(self, mid: float, side: str) -> float:
        half = self.spread / 2.0
        slip = self.slippage_per_side
        if side.upper() == "BUY":
            return mid - half - slip
        if side.upper() == "SELL":
            return mid + half + slip
        raise ValueError("side must be BUY or SELL")

    def commission(self, quantity: float) -> float:
        return abs(quantity) * self.commission_per_unit_round_trip
