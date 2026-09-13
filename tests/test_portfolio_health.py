from trading_for_money.portfolio import (
    ConstitutionInput,
    PortfolioHealthInput,
    PositionInput,
    build_portfolio_health,
)


TARGETS = {
    "CORE": 0.70,
    "OPPORTUNITY": 0.15,
    "GOLD_LAB": 0.05,
    "CASH": 0.10,
}


def test_empty_portfolio_is_fragile_but_reconciles_contribution():
    out = build_portfolio_health(
        PortfolioHealthInput(
            positions=(),
            target_weights=TARGETS,
            constitution=ConstitutionInput(),
            monthly_contribution=200,
        )
    )
    assert out.health_status == "FRAGILE"
    assert round(sum(x["amount"] for x in out.contribution_priority), 2) == 200


def test_diversified_policy_aligned_portfolio_scores_well():
    positions = (
        PositionInput("CORE1", "CORE", 1, 7000, 6500, "etf"),
        PositionInput("OPP1", "OPPORTUNITY", 1, 1500, 1400, "equity"),
        PositionInput("CASH", "CASH", 1, 1000, 1000, "cash"),
        PositionInput("GLD", "GOLD_LAB", 1, 500, 480, "commodity"),
    )
    out = build_portfolio_health(
        PortfolioHealthInput(
            positions=positions,
            target_weights=TARGETS,
            constitution=ConstitutionInput(
                emergency_fund_ready=True,
                max_single_position_pct=0.75,
            ),
            monthly_contribution=200,
            benchmark_return=0.03,
        )
    )
    assert out.health_score >= 85
    assert out.health_status == "STRONG"
    assert all(x["state"] == "IN_BAND" for x in out.rebalancing)


def test_single_position_concentration_is_penalized():
    positions = (
        PositionInput("NVDA", "OPPORTUNITY", 1, 8000, 6000, "equity"),
        PositionInput("CORE", "CORE", 1, 2000, 2000, "etf"),
    )
    out = build_portfolio_health(
        PortfolioHealthInput(
            positions=positions,
            target_weights=TARGETS,
            constitution=ConstitutionInput(max_single_position_pct=0.15),
        )
    )
    assert out.component_scores["concentration_discipline"] < 25
    assert any("single-position limit" in x for x in out.guardrails)


def test_underweight_core_directs_new_contributions():
    positions = (
        PositionInput("CORE", "CORE", 1, 3000, 3000, "etf"),
        PositionInput("OPP", "OPPORTUNITY", 1, 5000, 4500, "equity"),
        PositionInput("CASH", "CASH", 1, 2000, 2000, "cash"),
    )
    out = build_portfolio_health(
        PortfolioHealthInput(
            positions=positions,
            target_weights=TARGETS,
            constitution=ConstitutionInput(),
            monthly_contribution=200,
        )
    )
    core_band = next(x for x in out.rebalancing if x["bucket"] == "CORE")
    assert core_band["state"] == "UNDERWEIGHT"
    assert core_band["action"] == "DIRECT_NEW_CONTRIBUTIONS"
    core_plan = next(x for x in out.contribution_priority if x["bucket"] == "CORE")
    assert core_plan["amount"] > 0


def test_benchmark_difference_is_explicitly_context_only():
    positions = (
        PositionInput("CORE", "CORE", 1, 1100, 1000, "etf"),
    )
    out = build_portfolio_health(
        PortfolioHealthInput(
            positions=positions,
            target_weights=TARGETS,
            constitution=ConstitutionInput(max_single_position_pct=1.0),
            benchmark_return=0.05,
        )
    )
    assert round(out.portfolio_cost_basis_return, 4) == 0.10
    assert round(out.excess_vs_benchmark_context, 4) == 0.05
    assert out.diagnostics["benchmark_comparison_kind"] == "context_only"
