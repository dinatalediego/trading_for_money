"""Deterministic, non-executing capital allocation engine."""

from .engine import (
    AllocationInput,
    AllocationPlan,
    GoldEvidence,
    GoalInput,
    build_allocation_plan,
)

__all__ = [
    "AllocationInput",
    "AllocationPlan",
    "GoldEvidence",
    "GoalInput",
    "build_allocation_plan",
]
