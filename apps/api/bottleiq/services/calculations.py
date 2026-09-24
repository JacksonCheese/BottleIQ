"""Pure, deterministic inventory math. Zero-sales calendar days are included."""

from dataclasses import dataclass
from math import ceil, sqrt
from statistics import NormalDist

import numpy as np


@dataclass(frozen=True)
class Demand:
    average: float
    std: float
    safety: float
    reorder_point: float
    target: float
    days: float | None
    cases: int
    units: int


def stockout_before_replenishment(
    on_hand: int,
    average_daily_demand: float,
    safety_stock: float,
    lead_days: int,
    incoming_by_day: dict[int, int],
) -> bool:
    """Keep a risk visible if stock runs out before a confirmed delivery arrives."""
    if average_daily_demand <= 0:
        return False
    projected = float(on_hand) + incoming_by_day.get(0, 0)
    if projected <= 0:
        return True
    for day in range(1, lead_days + 1):
        projected += incoming_by_day.get(day, 0)
        projected -= average_daily_demand
        if projected <= 0:
            return True
    return projected <= safety_stock


def demand_metrics(
    daily: list[int],
    on_hand: int,
    lead_days: int,
    pack: int,
    target_days: int = 21,
    service_level: float = 0.95,
    incoming_units: int = 0,
) -> Demand:
    if not daily or pack <= 0 or lead_days < 0 or on_hand < 0 or incoming_units < 0:
        raise ValueError(
            "Demand needs calendar days, nonnegative stock/lead time, and a positive case pack"
        )
    if not 0.5 < service_level < 1 or target_days <= 0 or any(x < 0 for x in daily):
        raise ValueError("Invalid service level, target, or demand")
    average = float(np.mean(daily))
    std = float(np.std(daily, ddof=0))
    safety = NormalDist().inv_cdf(service_level) * std * sqrt(lead_days)
    point = average * lead_days + safety
    target = average * (lead_days + target_days) + safety
    # Weekly review: fill to target, even above reorder point; risk is a separate signal.
    cases = ceil(max(0, target - on_hand - incoming_units) / pack) if average > 0 else 0
    return Demand(
        average,
        std,
        safety,
        point,
        target,
        on_hand / average if average else None,
        cases,
        cases * pack,
    )


def abc_classes(revenues: dict[str, float]) -> dict[str, str]:
    total = sum(max(0, r) for r in revenues.values())
    cumulative = 0.0
    result = {}
    for key, revenue in sorted(revenues.items(), key=lambda item: (-item[1], item[0])):
        fraction_before = cumulative / total if total else 1
        result[key] = "A" if fraction_before < 0.8 else "B" if fraction_before < 0.95 else "C"
        cumulative += max(0, revenue)
    return result
