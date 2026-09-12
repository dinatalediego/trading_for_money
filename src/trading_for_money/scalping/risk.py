from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskPolicy:
    risk_fraction_per_trade: float = 0.0025
    max_daily_loss_fraction: float = 0.01
    max_consecutive_losses: int = 4
    cooldown_bars_after_loss: int = 3
    max_spread_to_atr: float = 0.20
    min_reward_to_risk: float = 1.25


@dataclass
class RiskState:
    start_day_equity: float
    current_equity: float
    consecutive_losses: int = 0
    cooldown_bars_remaining: int = 0
    open_positions: int = 0


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str


def evaluate_risk_gate(
    policy: RiskPolicy,
    state: RiskState,
    *,
    atr_value: float,
    spread: float,
    reward_to_risk: float,
) -> RiskDecision:
    if state.start_day_equity <= 0:
        return RiskDecision(False, "invalid start_day_equity")

    daily_loss = max(0.0, state.start_day_equity - state.current_equity)
    if daily_loss / state.start_day_equity >= policy.max_daily_loss_fraction:
        return RiskDecision(False, "daily loss limit reached")

    if state.consecutive_losses >= policy.max_consecutive_losses:
        return RiskDecision(False, "consecutive loss limit reached")

    if state.cooldown_bars_remaining > 0:
        return RiskDecision(False, "cooldown active")

    if state.open_positions > 0:
        return RiskDecision(False, "v0 permits one open position")

    if atr_value <= 0:
        return RiskDecision(False, "invalid ATR")

    if spread / atr_value > policy.max_spread_to_atr:
        return RiskDecision(False, "spread too large relative to ATR")

    if reward_to_risk < policy.min_reward_to_risk:
        return RiskDecision(False, "reward/risk below threshold")

    return RiskDecision(True, "passed")
