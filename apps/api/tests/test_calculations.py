import math
from statistics import NormalDist

import pytest

from bottleiq.services.calculations import (
    abc_classes,
    demand_metrics,
    stockout_before_replenishment,
)


def test_average_includes_zero_days():
    m = demand_metrics([0, 0, 0, 8], 2, 4, 12)
    assert m.average == 2
    assert m.days == 1


def test_safety_stock_and_reorder_point():
    m = demand_metrics([0, 2, 0, 2], 4, 4, 12)
    assert m.std == 1
    assert m.safety == pytest.approx(NormalDist().inv_cdf(0.95) * 2)
    assert m.reorder_point == pytest.approx(4 + m.safety)
    assert m.target == pytest.approx(25 + m.safety)


def test_fast_sku_case_rounding():
    m = demand_metrics([4] * 60, 8, 4, 12)
    assert m.target == 100
    assert m.cases == math.ceil((100 - 8) / 12) == 8
    assert m.units == 96
    assert m.reorder_point == 16


def test_confirmed_incoming_reduces_order_without_changing_days_of_supply():
    m = demand_metrics([4] * 60, 8, 4, 12, incoming_units=72)
    assert m.cases == 2
    assert m.units == 24
    assert m.days == 2
    assert m.reorder_point == 16


def test_stockout_risk_checks_arrival_timing():
    assert not stockout_before_replenishment(8, 4, 0, 4, {1: 72})
    assert stockout_before_replenishment(8, 4, 0, 4, {3: 72})
    assert stockout_before_replenishment(8, 4, 0, 4, {})


def test_normal_stock_no_order():
    m = demand_metrics([2] * 60, 70, 4, 12)
    assert m.days == 35
    assert m.cases == 0


def test_zero_demand_has_no_division_error_or_order():
    m = demand_metrics([0] * 90, 60, 4, 6)
    assert m.days is None
    assert m.cases == m.units == m.reorder_point == m.safety == 0


def test_overstock_never_orders():
    assert demand_metrics([1] * 60, 500, 4, 6).cases == 0


def test_zero_lead_time_has_no_safety_stock():
    assert demand_metrics([0, 4], 0, 0, 6).safety == 0


def test_abc_thresholds_and_zero_revenue():
    assert abc_classes({"a": 80, "b": 15, "c": 5}) == {"a": "A", "b": "B", "c": "C"}
    assert abc_classes({"a": 0, "b": 0}) == {"a": "C", "b": "C"}


def test_abc_threshold_crossing_item_stays_in_previous_class():
    assert abc_classes({"a": 90, "b": 10}) == {"a": "A", "b": "B"}


@pytest.mark.parametrize(
    "daily,hand,lead,pack,incoming",
    [
        ([], 1, 2, 12, 0),
        ([1], -1, 2, 12, 0),
        ([1], 1, -1, 12, 0),
        ([1], 1, 2, 0, 0),
        ([-1], 1, 2, 12, 0),
        ([1], 1, 2, 12, -1),
    ],
)
def test_invalid_inputs(daily, hand, lead, pack, incoming):
    with pytest.raises(ValueError):
        demand_metrics(daily, hand, lead, pack, incoming_units=incoming)
