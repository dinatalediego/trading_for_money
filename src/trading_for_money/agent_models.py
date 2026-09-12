from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal


Strength = Literal["strong", "moderate", "weak"]
Trend = Literal["up", "down", "flat"]
PaperAction = Literal["PAPER_BUY", "PAPER_SELL", "WATCH"]


@dataclass(frozen=True)
class MarketInsight:
    symbol: str
    label: str
    trend_20d: Trend
    trend_60d: Trend
    return_20d: float
    return_60d: float
    rel_20d_vs_spy: float
    vol_20d_annualized: float
    strength: Strength
    explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PaperProposal:
    proposal_id: str
    created_at: str
    symbol: str
    action: PaperAction
    strategy: str
    evidence: dict
    thesis: str
    invalidation: str
    confidence: Strength
    status: Literal["PENDING", "APPROVED", "REJECTED"] = "PENDING"

    @classmethod
    def new(
        cls,
        proposal_id: str,
        symbol: str,
        action: PaperAction,
        strategy: str,
        evidence: dict,
        thesis: str,
        invalidation: str,
        confidence: Strength,
    ) -> "PaperProposal":
        return cls(
            proposal_id=proposal_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            action=action,
            strategy=strategy,
            evidence=evidence,
            thesis=thesis,
            invalidation=invalidation,
            confidence=confidence,
        )

    def to_dict(self) -> dict:
        return asdict(self)
