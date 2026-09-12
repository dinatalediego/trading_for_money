from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from math import isfinite
from typing import Mapping, Sequence


BUCKETS = ("CORE", "OPPORTUNITY", "CASH", "GOLD_LAB")
ENGINE_VERSION = "capital_allocation_v1"


@dataclass(frozen=True)
class GoalInput:
    name: str
    target_amount: float
    target_date: date | None = None
    priority: int = 1


@dataclass(frozen=True)
class GoldEvidence:
    closed_trades: int = 0
    expectancy_r: float | None = None
    profit_factor: float | None = None
    max_drawdown_r: float | None = None
    worker_healthy: bool = False


@dataclass(frozen=True)
class AllocationInput:
    contribution_amount: float
    bucket_values: Mapping[str, float]
    target_weights: Mapping[str, float]
    goals: Sequence[GoalInput] = ()
    gold: GoldEvidence = GoldEvidence()
    opportunity_thesis_coverage: float = 0.0
    base_currency: str = "USD"
    as_of: date = field(default_factory=date.today)


@dataclass(frozen=True)
class AllocationItem:
    bucket: str
    amount: float
    pct_of_contribution: float
    priority: int
    rationale: str
    guardrail: str
    deployment_mode: str


@dataclass(frozen=True)
class AllocationPlan:
    engine_version: str
    base_currency: str
    contribution_amount: float
    portfolio_value: float
    gold_stage: str
    gold_rigor_score: int
    gold_allocation_factor: float
    goal_cash_reserve: float
    effective_target_weights: dict[str, float]
    items: tuple[AllocationItem, ...]
    diagnostics: dict

    def to_dict(self) -> dict:
        data = asdict(self)
        data["items"] = [asdict(item) for item in self.items]
        return data


def _money(value: float) -> float:
    return round(max(0.0, float(value)) + 1e-10, 2)


def _validate(inp: AllocationInput) -> None:
    if not isfinite(inp.contribution_amount) or inp.contribution_amount < 0:
        raise ValueError("contribution_amount must be finite and >= 0")

    missing = set(BUCKETS).difference(inp.target_weights)
    if missing:
        raise ValueError(f"missing target weights: {sorted(missing)}")

    total_weight = sum(float(inp.target_weights[b]) for b in BUCKETS)
    if abs(total_weight - 1.0) > 1e-6:
        raise ValueError("target weights must sum to 1")

    for bucket in BUCKETS:
        weight = float(inp.target_weights[bucket])
        value = float(inp.bucket_values.get(bucket, 0.0))
        if weight < 0 or weight > 1:
            raise ValueError(f"invalid target weight for {bucket}")
        if value < 0 or not isfinite(value):
            raise ValueError(f"invalid bucket value for {bucket}")

    if not 0 <= inp.opportunity_thesis_coverage <= 1:
        raise ValueError("opportunity_thesis_coverage must be between 0 and 1")


def gold_maturity(evidence: GoldEvidence) -> tuple[str, float, int, list[str]]:
    """Return stage, allocation factor, rigor score, and evidence notes.

    The allocation factor caps *new research capital* directed to GOLD_LAB.
    It never authorizes live broker execution.
    """
    n = max(0, int(evidence.closed_trades))
    expectancy = evidence.expectancy_r
    pf = evidence.profit_factor
    dd = evidence.max_drawdown_r

    if n < 30:
        stage, sample_factor, sample_score = "DATA_COLLECTION", 0.0, round(n / 30 * 20)
    elif n < 100:
        stage, sample_factor, sample_score = "EARLY_EVIDENCE", 0.25, 25
    elif n < 300:
        stage, sample_factor, sample_score = "PAPER_VALIDATION", 0.50, 30
    elif n < 500:
        stage, sample_factor, sample_score = "ADVANCED_PAPER", 0.75, 35
    else:
        stage, sample_factor, sample_score = "MATURE_PAPER_SAMPLE", 1.0, 40

    positive_edge = expectancy is not None and expectancy > 0
    pf_ok = pf is not None and pf >= 1.20
    dd_ok = dd is None or dd <= 12.0

    evidence_factor = 1.0
    notes = [f"{n} paper trades closed"]

    if n < 30:
        evidence_factor = 0.0
        notes.append("sample too small for capital promotion")
    else:
        if not positive_edge:
            evidence_factor *= 0.25
            notes.append("expectancy is not yet positive")
        else:
            notes.append(f"expectancy {expectancy:+.2f}R")

        if not pf_ok:
            evidence_factor *= 0.70
            notes.append("profit factor below 1.20 or unavailable")
        else:
            notes.append(f"profit factor {pf:.2f}")

        if not dd_ok:
            evidence_factor *= 0.50
            notes.append("drawdown exceeds the research tolerance")

        if not evidence.worker_healthy:
            evidence_factor *= 0.50
            notes.append("worker health is not confirmed")

    allocation_factor = max(0.0, min(1.0, sample_factor * evidence_factor))

    edge_score = 0
    if expectancy is not None:
        edge_score += max(0, min(20, round((expectancy + 0.05) / 0.35 * 20)))
    if pf is not None:
        edge_score += max(0, min(15, round((pf - 0.8) / 0.8 * 15)))
    risk_score = 15 if dd_ok else 5
    worker_score = 10 if evidence.worker_healthy else 0
    rigor = max(0, min(100, sample_score + edge_score + risk_score + worker_score))

    return stage, allocation_factor, rigor, notes


def _months_until(as_of: date, target: date) -> int:
    months = (target.year - as_of.year) * 12 + target.month - as_of.month
    if target.day > as_of.day:
        months += 1
    return max(0, months)


def _goal_reserve(
    goals: Sequence[GoalInput],
    *,
    portfolio_value: float,
    contribution: float,
    as_of: date,
) -> tuple[float, list[dict]]:
    """Reserve at most 30% of the monthly contribution for near-term goals.

    Only goals due within 24 months affect the allocation automatically.
    Longer-horizon goals are reported but do not override the strategic weights.
    """
    if contribution <= 0:
        return 0.0, []

    analyses: list[dict] = []
    candidates: list[tuple[int, float, GoalInput]] = []

    for goal in goals:
        if goal.target_amount <= 0 or goal.target_date is None:
            continue

        months = _months_until(as_of, goal.target_date)
        shortfall = max(0.0, float(goal.target_amount) - portfolio_value)
        monthly_needed = shortfall / max(1, months) if shortfall > 0 else 0.0
        analyses.append(
            {
                "name": goal.name,
                "months_remaining": months,
                "shortfall": round(shortfall, 2),
                "monthly_needed": round(monthly_needed, 2),
                "priority": goal.priority,
                "affects_cash_reserve": 0 < months <= 24 and shortfall > 0,
            }
        )
        if 0 < months <= 24 and shortfall > 0:
            candidates.append((goal.priority, monthly_needed, goal))

    if not candidates:
        return 0.0, analyses

    candidates.sort(key=lambda x: (-x[0], x[2].target_date or as_of))
    desired = max(monthly for _, monthly, _ in candidates)
    reserve = min(contribution * 0.30, desired)
    return _money(reserve), analyses


def _normalize_targets(
    targets: Mapping[str, float],
    gold_factor: float,
) -> dict[str, float]:
    adjusted = {b: float(targets[b]) for b in BUCKETS}
    adjusted["GOLD_LAB"] *= gold_factor

    total = sum(adjusted.values())
    if total <= 0:
        return {"CORE": 1.0, "OPPORTUNITY": 0.0, "CASH": 0.0, "GOLD_LAB": 0.0}

    return {b: adjusted[b] / total for b in BUCKETS}


def _allocate_remaining(
    remaining: float,
    virtual_values: dict[str, float],
    effective_targets: dict[str, float],
    post_total: float,
) -> dict[str, float]:
    plan = {b: 0.0 for b in BUCKETS}
    if remaining <= 0:
        return plan

    desired = {b: effective_targets[b] * post_total for b in BUCKETS}
    shortages = {b: max(0.0, desired[b] - virtual_values[b]) for b in BUCKETS}
    shortage_total = sum(shortages.values())

    if shortage_total > 1e-9:
        for b in BUCKETS:
            plan[b] = remaining * shortages[b] / shortage_total
    else:
        for b in BUCKETS:
            plan[b] = remaining * effective_targets[b]

    return plan


def build_allocation_plan(inp: AllocationInput) -> AllocationPlan:
    """Create an explainable contribution plan without executing investments."""
    _validate(inp)

    contribution = float(inp.contribution_amount)
    values = {b: float(inp.bucket_values.get(b, 0.0)) for b in BUCKETS}
    portfolio_value = sum(values.values())

    stage, gold_factor, rigor, gold_notes = gold_maturity(inp.gold)
    effective_targets = _normalize_targets(inp.target_weights, gold_factor)

    goal_cash, goal_analyses = _goal_reserve(
        inp.goals,
        portfolio_value=portfolio_value,
        contribution=contribution,
        as_of=inp.as_of,
    )

    allocations = {b: 0.0 for b in BUCKETS}
    allocations["CASH"] = goal_cash

    virtual = values.copy()
    virtual["CASH"] += goal_cash

    remaining = max(0.0, contribution - goal_cash)
    post_total = portfolio_value + contribution
    gap_allocations = _allocate_remaining(
        remaining,
        virtual,
        effective_targets,
        post_total,
    )
    for b in BUCKETS:
        allocations[b] += gap_allocations[b]

    # Round in integer cents so the proposal always reconciles exactly.
    contribution_cents = round(contribution * 100)
    rounded_cents = {b: round(allocations[b] * 100) for b in BUCKETS}
    delta_cents = contribution_cents - sum(rounded_cents.values())
    if delta_cents:
        priority_bucket = max(BUCKETS, key=lambda b: allocations[b])
        rounded_cents[priority_bucket] += delta_cents
    rounded = {b: rounded_cents[b] / 100 for b in BUCKETS}

    target_post = {b: effective_targets[b] * post_total for b in BUCKETS}
    actual_post = {b: values[b] + rounded[b] for b in BUCKETS}

    items: list[AllocationItem] = []
    ranked = sorted(BUCKETS, key=lambda b: rounded[b], reverse=True)

    for priority, bucket in enumerate(ranked, start=1):
        amount = rounded[bucket]
        pct_contribution = amount / contribution if contribution > 0 else 0.0
        current_share = values[bucket] / portfolio_value if portfolio_value > 0 else 0.0
        target_share = effective_targets[bucket]

        if bucket == "GOLD_LAB":
            if gold_factor <= 0:
                rationale = (
                    f"Gold Alpha is in {stage}; no new contribution is promoted "
                    "to GOLD_LAB until the evidence gate improves."
                )
            else:
                rationale = (
                    f"GOLD_LAB is capped at {gold_factor:.0%} of its strategic target "
                    f"because Gold Alpha is in {stage}."
                )
            guardrail = (
                "Research reserve only. This recommendation never authorizes live "
                "broker execution or autonomous real-money trading."
            )
            mode = "RESEARCH_ONLY"
        elif bucket == "OPPORTUNITY":
            rationale = (
                f"Current share {current_share:.1%}; effective target {target_share:.1%}. "
                "Allocation follows the post-contribution target gap."
            )
            if inp.opportunity_thesis_coverage < 0.50:
                guardrail = (
                    "Less than half of Opportunity positions have both thesis and "
                    "invalidation. Keep this amount as an earmarked reserve until a "
                    "written thesis exists."
                )
                mode = "RESERVE_ONLY"
            else:
                guardrail = (
                    "Deploy manually only into opportunities with an explicit thesis, "
                    "invalidation and position-size limit."
                )
                mode = "MANUAL"
        elif bucket == "CASH":
            rationale = (
                f"Current share {current_share:.1%}; effective target {target_share:.1%}. "
                f"Near-term goal overlay reserved {goal_cash:.2f} {inp.base_currency} "
                "before strategic rebalancing."
            )
            guardrail = "Cash remains uninvested until the user chooses a destination."
            mode = "RESERVE_ONLY"
        else:
            rationale = (
                f"Current share {current_share:.1%}; effective target {target_share:.1%}. "
                "CORE receives capital according to the largest post-contribution "
                "strategic shortfall."
            )
            guardrail = (
                "The engine recommends a bucket amount, not a security. Final instrument "
                "selection and order placement remain manual."
            )
            mode = "MANUAL"

        items.append(
            AllocationItem(
                bucket=bucket,
                amount=amount,
                pct_of_contribution=round(pct_contribution, 6),
                priority=priority,
                rationale=rationale,
                guardrail=guardrail,
                deployment_mode=mode,
            )
        )

    diagnostics = {
        "current_bucket_values": {b: round(values[b], 2) for b in BUCKETS},
        "post_contribution_bucket_values": {
            b: round(actual_post[b], 2) for b in BUCKETS
        },
        "post_contribution_target_values": {
            b: round(target_post[b], 2) for b in BUCKETS
        },
        "original_target_weights": {
            b: round(float(inp.target_weights[b]), 6) for b in BUCKETS
        },
        "goal_analysis": goal_analyses,
        "gold_evidence_notes": gold_notes,
        "opportunity_thesis_coverage": round(inp.opportunity_thesis_coverage, 4),
        "non_execution_notice": (
            "This plan is advisory. It creates no broker/exchange order and moves no money."
        ),
    }

    return AllocationPlan(
        engine_version=ENGINE_VERSION,
        base_currency=inp.base_currency,
        contribution_amount=_money(contribution),
        portfolio_value=_money(portfolio_value),
        gold_stage=stage,
        gold_rigor_score=rigor,
        gold_allocation_factor=round(gold_factor, 6),
        goal_cash_reserve=goal_cash,
        effective_target_weights={
            b: round(effective_targets[b], 6) for b in BUCKETS
        },
        items=tuple(items),
        diagnostics=diagnostics,
    )
