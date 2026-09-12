from datetime import date, timedelta

from trading_for_money.allocation import (
    AllocationInput,
    GoldEvidence,
    GoalInput,
    build_allocation_plan,
)


TARGETS = {
    "CORE": 0.70,
    "OPPORTUNITY": 0.15,
    "GOLD_LAB": 0.05,
    "CASH": 0.10,
}


def _amounts(plan):
    return {item.bucket: item.amount for item in plan.items}


def test_immature_gold_gets_no_new_capital():
    plan = build_allocation_plan(
        AllocationInput(
            contribution_amount=1000,
            bucket_values={b: 0 for b in TARGETS},
            target_weights=TARGETS,
            gold=GoldEvidence(closed_trades=0, worker_healthy=True),
        )
    )
    amounts = _amounts(plan)
    assert amounts["GOLD_LAB"] == 0
    assert round(sum(amounts.values()), 2) == 1000
    assert plan.gold_stage == "DATA_COLLECTION"


def test_positive_mature_gold_can_receive_research_allocation():
    plan = build_allocation_plan(
        AllocationInput(
            contribution_amount=1000,
            bucket_values={
                "CORE": 7000,
                "OPPORTUNITY": 1500,
                "GOLD_LAB": 500,
                "CASH": 1000,
            },
            target_weights=TARGETS,
            gold=GoldEvidence(
                closed_trades=600,
                expectancy_r=0.20,
                profit_factor=1.45,
                max_drawdown_r=7.0,
                worker_healthy=True,
            ),
            opportunity_thesis_coverage=1.0,
        )
    )
    amounts = _amounts(plan)
    assert amounts["GOLD_LAB"] > 0
    assert plan.gold_allocation_factor == 1.0
    assert round(sum(amounts.values()), 2) == 1000


def test_near_term_goal_creates_cash_reserve():
    plan = build_allocation_plan(
        AllocationInput(
            contribution_amount=1000,
            bucket_values={b: 0 for b in TARGETS},
            target_weights=TARGETS,
            goals=(
                GoalInput(
                    name="Short-term goal",
                    target_amount=5000,
                    target_date=date.today() + timedelta(days=180),
                    priority=5,
                ),
            ),
        )
    )
    assert plan.goal_cash_reserve == 300.0
    amounts = _amounts(plan)
    assert amounts["CASH"] >= 300.0
    assert round(sum(amounts.values()), 2) == 1000


def test_opportunity_low_thesis_coverage_is_reserve_only():
    plan = build_allocation_plan(
        AllocationInput(
            contribution_amount=500,
            bucket_values={b: 0 for b in TARGETS},
            target_weights=TARGETS,
            opportunity_thesis_coverage=0.0,
        )
    )
    item = next(i for i in plan.items if i.bucket == "OPPORTUNITY")
    assert item.deployment_mode == "RESERVE_ONLY"


def test_rebalancing_biases_underweight_core():
    plan = build_allocation_plan(
        AllocationInput(
            contribution_amount=1000,
            bucket_values={
                "CORE": 1000,
                "OPPORTUNITY": 3000,
                "GOLD_LAB": 0,
                "CASH": 1000,
            },
            target_weights=TARGETS,
            gold=GoldEvidence(closed_trades=0, worker_healthy=True),
            opportunity_thesis_coverage=1.0,
        )
    )
    amounts = _amounts(plan)
    assert amounts["CORE"] > amounts["OPPORTUNITY"]
