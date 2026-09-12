from __future__ import annotations

import hashlib
import json

import pandas as pd

from .agent_models import PaperProposal


def _proposal_id(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def relative_strength_proposals(
    insights: pd.DataFrame,
    rel_threshold: float = 0.03,
    min_return_60d: float = 0.05,
) -> list[PaperProposal]:
    """Generate *paper-only* research proposals.

    The rule is intentionally simple and auditable:
    - PAPER_BUY when 20d relative strength vs SPY exceeds rel_threshold
      and 60d absolute return is above min_return_60d.
    - WATCH otherwise.

    This function does not submit or route real orders.
    """
    proposals: list[PaperProposal] = []

    for row in insights.to_dict(orient="records"):
        if row["symbol"] == "SPY":
            continue

        qualifies = (
            row["rel_20d_vs_spy"] >= rel_threshold
            and row["return_60d"] >= min_return_60d
        )
        action = "PAPER_BUY" if qualifies else "WATCH"

        evidence = {
            "return_20d": row["return_20d"],
            "return_60d": row["return_60d"],
            "rel_20d_vs_spy": row["rel_20d_vs_spy"],
            "vol_20d_annualized": row["vol_20d_annualized"],
        }
        identity = {
            "symbol": row["symbol"],
            "action": action,
            "strategy": "relative_strength_v0",
            **evidence,
        }

        proposals.append(
            PaperProposal.new(
                proposal_id=_proposal_id(identity),
                symbol=row["symbol"],
                action=action,
                strategy="relative_strength_v0",
                evidence=evidence,
                thesis=(
                    "Paper-test whether persistent relative strength continues over "
                    "the next evaluation horizon."
                ),
                invalidation=(
                    "Relative strength vs SPY falls below zero or the 60-day trend "
                    "turns negative."
                ),
                confidence=row["strength"],
            )
        )

    return proposals
