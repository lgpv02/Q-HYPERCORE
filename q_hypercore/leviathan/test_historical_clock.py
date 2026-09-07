"""
Tests del Invariante T.2 (Strict Monotonic Time Progress).

Verifican que el HistoricalClock nunca permita retroceder ni permanecer
en el mismo as_of dos veces, y que ClockContext sea realmente inmutable.
"""
from datetime import datetime, timedelta

import pytest

from historical_clock import HistoricalClock, ClockContext, ClockRegressionError


def test_first_advance_sets_current():
    clock = HistoricalClock()
    ctx = clock.advance(datetime(2024, 1, 1), cycle_index=0)
    assert clock.current is ctx
    assert ctx.as_of == datetime(2024, 1, 1)
    assert ctx.cycle_index == 0


def test_current_raises_before_first_advance():
    clock = HistoricalClock()
    with pytest.raises(RuntimeError):
        _ = clock.current


def test_strictly_increasing_advance_is_allowed():
    clock = HistoricalClock()
    clock.advance(datetime(2024, 1, 1), cycle_index=0)
    ctx2 = clock.advance(datetime(2024, 1, 2), cycle_index=1)
    assert ctx2.as_of == datetime(2024, 1, 2)


def test_same_timestamp_twice_raises_regression():
    clock = HistoricalClock()
    ts = datetime(2024, 1, 1)
    clock.advance(ts, cycle_index=0)
    with pytest.raises(ClockRegressionError):
        clock.advance(ts, cycle_index=1)


def test_earlier_timestamp_raises_regression():
    clock = HistoricalClock()
    clock.advance(datetime(2024, 1, 5), cycle_index=0)
    with pytest.raises(ClockRegressionError):
        clock.advance(datetime(2024, 1, 4), cycle_index=1)


def test_clock_context_is_immutable():
    clock = HistoricalClock()
    ctx = clock.advance(datetime(2024, 1, 1), cycle_index=0)
    with pytest.raises(Exception):
        ctx.as_of = datetime(2024, 1, 2)  # dataclass frozen=True debe impedirlo


def test_regression_message_includes_both_timestamps():
    clock = HistoricalClock()
    clock.advance(datetime(2024, 1, 5), cycle_index=0)
    try:
        clock.advance(datetime(2024, 1, 1), cycle_index=1)
        assert False, "debería haber lanzado ClockRegressionError"
    except ClockRegressionError as e:
        assert "2024-01-05" in str(e)
        assert "2024-01-01" in str(e)
