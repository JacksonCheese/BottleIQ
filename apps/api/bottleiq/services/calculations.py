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


def demand_metrics(
    daily: list[int],
    on_hand: int,
    lead_days: int,
    pack: int,
    target_days: int = 21,
    service_level: float = 0.95,
) -> Demand:
    if not daily or pack <= 0 or lead_days < 0 or on_hand < 0:
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
    cases = ceil(max(0, target - on_hand) / pack) if average > 0 else 0
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
