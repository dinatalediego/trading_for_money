from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Mapping, Sequence


BUCKETS = ("CORE", "OPPORTUNITY", "CASH", "GOLD_LAB")
ENGINE_VERSION = "portfolio_health_v1"


@dataclass(frozen=True)
class PositionInput:
    symbol: str
    bucket: str
    quantity: float
    market_price: float
    avg_cost: float | None = None
    asset_class: str = "other"


@dataclass(frozen=True)
class ConstitutionInput:
    horizon_years: int = 10
    emergency_fund_months: int = 6
    emergency_fund_ready: bool = False
    max_single_position_pct: float = 0.15
    max_sector_pct: float = 0.30
    max_opportunity_pct: float = 0.20
    max_gold_lab_pct: float = 0.05
    max_drawdown_tolerance_pct: float = 0.25
    leverage_policy: str = "NONE"
    rebalance_method: str = "CONTRIBUTIONS_FIRST"
    core_band_pp: float = 0.05
    opportunity_band_pp: float = 0.03
    cash_band_pp: float = 0.03
    gold_lab_band_pp: float = 0.02
    benchmark_symbol: str = "SPY"
    benchmark_window_days: int = 60
    decision_cooldown_hours: int = 24
    opportunity_requires_thesis: bool = True
    gold_live_allowed: bool = False


@dataclass(frozen=True)
class PortfolioHealthInput:
    positions: Sequence[PositionInput]
    target_weights: Mapping[str, float]
    constitution: ConstitutionInput
    monthly_contribution: float = 0.0
    benchmark_return: float | None = None
    benchmark_price: float | None = None
    base_currency: str = "USD"


@dataclass(frozen=True)
class PortfolioHealthResult:
    engine_version: str
    health_score: int
    health_status: str
    portfolio_value: float
    total_cost_basis: float
    unrealized_pnl: float
    portfolio_cost_basis_return: float | None
    benchmark_symbol: str
    benchmark_return: float | None
    benchmark_price: float | None
    excess_vs_benchmark_context: float | None
    component_scores: dict
    bucket_values: dict
    bucket_weights: dict
    position_metrics: tuple[dict, ...]
    attribution: dict
    rebalancing: tuple[dict, ...]
    contribution_priority: tuple[dict, ...]
    guardrails: tuple[str, ...]
    diagnostics: dict

    def to_dict(self) -> dict:
        data = asdict(self)
        data["position_metrics"] = list(self.position_metrics)
        data["rebalancing"] = list(self.rebalancing)
        data["contribution_priority"] = list(self.contribution_priority)
        data["guardrails"] = list(self.guardrails)
        return data


def _validate(inp: PortfolioHealthInput) -> None:
    if inp.monthly_contribution < 0 or not isfinite(inp.monthly_contribution):
        raise ValueError("monthly_contribution must be finite and >= 0")

    missing = set(BUCKETS).difference(inp.target_weights)
    if missing:
        raise ValueError(f"missing target weights: {sorted(missing)}")

    total_weight = sum(float(inp.target_weights[b]) for b in BUCKETS)
    if abs(total_weight - 1.0) > 1e-6:
        raise ValueError("target weights must sum to 1")

    for b in BUCKETS:
        if not 0 <= float(inp.target_weights[b]) <= 1:
            raise ValueError(f"invalid target weight for {b}")

    c = inp.constitution
    if c.horizon_years < 1:
        raise ValueError("horizon_years must be >= 1")
    if not 0 < c.max_single_position_pct <= 1:
        raise ValueError("max_single_position_pct must be in (0, 1]")

    for p in inp.positions:
        if p.bucket not in BUCKETS:
            raise ValueError(f"invalid bucket for {p.symbol}: {p.bucket}")
        if p.quantity < 0 or p.market_price < 0:
            raise ValueError(f"negative quantity/price for {p.symbol}")


def _score_ratio(actual: float, desired: float, points: int) -> int:
    if desired <= 0:
        return points
    ratio = min(1.0, max(0.0, actual / desired))
    return round(points * ratio)


def _status(score: int) -> str:
    if score >= 85:
        return "STRONG"
    if score >= 70:
        return "HEALTHY_WITH_GAPS"
    if score >= 50:
        return "NEEDS_ATTENTION"
    return "FRAGILE"


def _band_for(bucket: str, c: ConstitutionInput) -> float:
    return {
        "CORE": c.core_band_pp,
        "OPPORTUNITY": c.opportunity_band_pp,
        "CASH": c.cash_band_pp,
        "GOLD_LAB": c.gold_lab_band_pp,
    }[bucket]


def build_portfolio_health(inp: PortfolioHealthInput) -> PortfolioHealthResult:
    """Evaluate portfolio structure without issuing or executing orders.

    Benchmark comparison is explicitly contextual: current-holdings cost-basis return
    is not a time-weighted return and should not be presented as exact alpha.
    """
    _validate(inp)

    position_metrics: list[dict] = []
    bucket_values = {b: 0.0 for b in BUCKETS}
    bucket_cost = {b: 0.0 for b in BUCKETS}
    total_value = 0.0
    total_cost = 0.0

    for p in inp.positions:
        value = float(p.quantity) * float(p.market_price)
        cost = (
            float(p.quantity) * float(p.avg_cost)
            if p.avg_cost is not None and p.avg_cost >= 0
            else value
        )
        pnl = value - cost
        ret = pnl / cost if cost > 0 else None

        total_value += value
        total_cost += cost
        bucket_values[p.bucket] += value
        bucket_cost[p.bucket] += cost

        position_metrics.append(
            {
                "symbol": p.symbol,
                "bucket": p.bucket,
                "asset_class": p.asset_class,
                "market_value": round(value, 2),
                "cost_basis": round(cost, 2),
                "unrealized_pnl": round(pnl, 2),
                "return_pct": ret,
            }
        )

    total_pnl = total_value - total_cost
    cost_basis_return = total_pnl / total_cost if total_cost > 0 else None
    bucket_weights = {
        b: (bucket_values[b] / total_value if total_value > 0 else 0.0)
        for b in BUCKETS
    }

    for p in position_metrics:
        p["portfolio_weight"] = (
            p["market_value"] / total_value if total_value > 0 else 0.0
        )
        p["pnl_contribution"] = (
            p["unrealized_pnl"] / total_pnl
            if abs(total_pnl) > 1e-12
            else None
        )

    position_metrics.sort(key=lambda x: x["market_value"], reverse=True)

    target = {b: float(inp.target_weights[b]) for b in BUCKETS}
    c = inp.constitution

    # 1) Core integrity (25)
    core_floor = max(0.0, target["CORE"] - c.core_band_pp)
    core_integrity = (
        25
        if bucket_weights["CORE"] >= core_floor
        else _score_ratio(bucket_weights["CORE"], max(core_floor, 0.01), 25)
    )

    # 2) Allocation discipline (25): penalize weighted absolute drift.
    total_abs_drift = sum(abs(bucket_weights[b] - target[b]) for b in BUCKETS)
    allocation_discipline = round(25 * max(0.0, 1.0 - min(1.0, total_abs_drift / 0.50)))

    # 3) Concentration discipline (25)
    max_position_weight = max(
        (float(p["portfolio_weight"]) for p in position_metrics),
        default=0.0,
    )
    if max_position_weight <= c.max_single_position_pct:
        concentration = 25
    else:
        excess = max_position_weight - c.max_single_position_pct
        concentration = round(25 * max(0.0, 1.0 - excess / max(c.max_single_position_pct, 0.01)))

    # 4) Speculation discipline (15)
    opp_ok = bucket_weights["OPPORTUNITY"] <= c.max_opportunity_pct + 1e-9
    gold_ok = bucket_weights["GOLD_LAB"] <= c.max_gold_lab_pct + 1e-9
    speculation = 15 if opp_ok and gold_ok else 8 if (opp_ok or gold_ok) else 0

    # 5) Financial resilience (10)
    resilience = 10 if c.emergency_fund_ready else 3

    components = {
        "core_integrity": core_integrity,
        "allocation_discipline": allocation_discipline,
        "concentration_discipline": concentration,
        "speculation_discipline": speculation,
        "financial_resilience": resilience,
    }
    score = int(sum(components.values()))

    # Current holdings attribution: useful, but not TWR.
    bucket_attribution = {}
    for b in BUCKETS:
        pnl = bucket_values[b] - bucket_cost[b]
        ret = pnl / bucket_cost[b] if bucket_cost[b] > 0 else None
        bucket_attribution[b] = {
            "market_value": round(bucket_values[b], 2),
            "cost_basis": round(bucket_cost[b], 2),
            "unrealized_pnl": round(pnl, 2),
            "return_pct": ret,
            "portfolio_weight": bucket_weights[b],
            "pnl_contribution": (
                pnl / total_pnl if abs(total_pnl) > 1e-12 else None
            ),
        }

    excess_context = None
    if cost_basis_return is not None and inp.benchmark_return is not None:
        excess_context = cost_basis_return - inp.benchmark_return

    # Rebalancing bands.
    rebalancing = []
    underweight_gap = {}
    for b in BUCKETS:
        band = _band_for(b, c)
        lower = max(0.0, target[b] - band)
        upper = min(1.0, target[b] + band)
        actual = bucket_weights[b]

        if actual < lower - 1e-9:
            state = "UNDERWEIGHT"
            action = "DIRECT_NEW_CONTRIBUTIONS"
        elif actual > upper + 1e-9:
            state = "OVERWEIGHT"
            action = "PAUSE_NEW_CONTRIBUTIONS"
        else:
            state = "IN_BAND"
            action = "HOLD_POLICY"

        gap_to_target = max(0.0, target[b] * (total_value + inp.monthly_contribution) - bucket_values[b])
        underweight_gap[b] = gap_to_target if state == "UNDERWEIGHT" else 0.0

        rebalancing.append(
            {
                "bucket": b,
                "actual_weight": actual,
                "target_weight": target[b],
                "lower_band": lower,
                "upper_band": upper,
                "drift_pp": (actual - target[b]) * 100,
                "state": state,
                "action": action,
            }
        )

    # Contribution-first priority amounts: informational only.
    contribution_priority = []
    remaining = float(inp.monthly_contribution)
    gap_sum = sum(underweight_gap.values())
    if remaining > 0:
        if gap_sum > 0:
            amounts = {
                b: remaining * underweight_gap[b] / gap_sum
                for b in BUCKETS
            }
        else:
            # If all buckets are in band, new cash follows target weights.
            amounts = {b: remaining * target[b] for b in BUCKETS}
    else:
        amounts = {b: 0.0 for b in BUCKETS}

    cents = {b: round(amounts[b] * 100) for b in BUCKETS}
    delta = round(remaining * 100) - sum(cents.values())
    if delta:
        recipient = max(BUCKETS, key=lambda b: amounts[b])
        cents[recipient] += delta

    for b in sorted(BUCKETS, key=lambda x: cents[x], reverse=True):
        contribution_priority.append(
            {
                "bucket": b,
                "amount": cents[b] / 100,
                "reason": next(x["state"] for x in rebalancing if x["bucket"] == b),
            }
        )

    guardrails = []
    if not c.emergency_fund_ready:
        guardrails.append(
            f"Emergency reserve is not marked ready; target is {c.emergency_fund_months} months."
        )
    if max_position_weight > c.max_single_position_pct:
        top = position_metrics[0]["symbol"] if position_metrics else "largest position"
        guardrails.append(
            f"{top} exceeds the constitution's single-position limit "
            f"({max_position_weight:.1%} vs {c.max_single_position_pct:.1%})."
        )
    if not opp_ok:
        guardrails.append(
            "OPPORTUNITY exceeds its constitutional maximum; pause new tactical capital."
        )
    if not gold_ok:
        guardrails.append(
            "GOLD_LAB exceeds its constitutional maximum; do not allocate additional capital."
        )
    if c.leverage_policy == "NONE":
        guardrails.append("Constitution prohibits leverage.")
    if not c.gold_live_allowed:
        guardrails.append("Gold Alpha remains research/paper-only under the constitution.")

    diagnostics = {
        "benchmark_comparison_kind": "context_only",
        "benchmark_warning": (
            "Current-holdings cost-basis return is not time-weighted. Exact alpha/TWR "
            "requires longitudinal snapshots and dated cash flows."
        ),
        "max_position_weight": max_position_weight,
        "total_absolute_allocation_drift": total_abs_drift,
        "rebalance_method": c.rebalance_method,
        "decision_cooldown_hours": c.decision_cooldown_hours,
        "non_execution_notice": (
            "Portfolio Health and Rebalancing Bands are advisory. They create no broker order."
        ),
    }

    return PortfolioHealthResult(
        engine_version=ENGINE_VERSION,
        health_score=score,
        health_status=_status(score),
        portfolio_value=round(total_value, 2),
        total_cost_basis=round(total_cost, 2),
        unrealized_pnl=round(total_pnl, 2),
        portfolio_cost_basis_return=cost_basis_return,
        benchmark_symbol=c.benchmark_symbol,
        benchmark_return=inp.benchmark_return,
        benchmark_price=inp.benchmark_price,
        excess_vs_benchmark_context=excess_context,
        component_scores=components,
        bucket_values={b: round(bucket_values[b], 2) for b in BUCKETS},
        bucket_weights=bucket_weights,
        position_metrics=tuple(position_metrics),
        attribution={
            "by_bucket": bucket_attribution,
            "interpretation": (
                "Attribution is based on unrealized P&L of current holdings, not a full "
                "time-weighted performance history."
            ),
        },
        rebalancing=tuple(rebalancing),
        contribution_priority=tuple(contribution_priority),
        guardrails=tuple(guardrails),
        diagnostics=diagnostics,
    )
