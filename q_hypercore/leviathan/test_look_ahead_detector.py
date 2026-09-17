"""
Tests del Invariante T.1 (Temporal Causal Constraint) y T.3 (Kernel
Isolation of Leakage), implementados por LookAheadDetector.

Casos cubiertos:
- Un dato UNAVAILABLE siempre pasa (no hay nada que auditar).
- Un dato HISTORICAL con timestamp <= as_of pasa sin problema.
- Un dato HISTORICAL con timestamp > as_of dispara SystemContaminationHalt
  (esto es, literalmente, el bug que causó 729 trades sobre 730 velas).
- Un dato STABLE_STUB se trata igual que HISTORICAL para efectos de
  la validación temporal (ambos deben traer source_timestamp válido).
- Un dato declarado HISTORICAL/STABLE_STUB sin source_timestamp también
  se considera contaminación, porque no se puede auditar.
"""
from datetime import datetime, timedelta

import pytest

from q_hypercore.leviathan.look_ahead_detector import (
    LookAheadDetector,
    CollectorResult,
    DataStatus,
    SystemContaminationHalt,
)

AS_OF = datetime(2024, 6, 15)


@pytest.fixture
def detector() -> LookAheadDetector:
    return LookAheadDetector()


def test_unavailable_always_passes(detector):
    result = CollectorResult(
        source_name="OICollector",
        status=DataStatus.UNAVAILABLE,
        data=None,
        source_timestamp=None,
    )
    # no debe lanzar ninguna excepción
    guarded = detector.guard(result, AS_OF)
    assert guarded is result


def test_historical_data_before_as_of_passes(detector):
    result = CollectorResult(
        source_name="WhaleCollector",
        status=DataStatus.HISTORICAL,
        data={"net_flow_usd": 1_500_000},
        source_timestamp=AS_OF - timedelta(days=1),
    )
    guarded = detector.guard(result, AS_OF)
    assert guarded is result


def test_historical_data_exactly_at_as_of_passes(detector):
    result = CollectorResult(
        source_name="FundingCollector",
        status=DataStatus.HISTORICAL,
        data={"rate": 0.0001},
        source_timestamp=AS_OF,
    )
    guarded = detector.guard(result, AS_OF)
    assert guarded is result


def test_historical_data_after_as_of_raises_contamination(detector):
    """
    Este es el caso central: reproduce exactamente el bug detectado en
    la auditoría — un collector devolviendo datos posteriores al día
    que se está simulando.
    """
    result = CollectorResult(
        source_name="LiquidationCollector",
        status=DataStatus.HISTORICAL,
        data={"cluster_usd": 8_000_000},
        source_timestamp=AS_OF + timedelta(days=1),
    )
    with pytest.raises(SystemContaminationHalt):
        detector.guard(result, AS_OF)


def test_stable_stub_after_as_of_also_raises(detector):
    """STABLE_STUB no es un pase libre: sigue sujeto al Invariante T.1."""
    result = CollectorResult(
        source_name="MacroCollector",
        status=DataStatus.STABLE_STUB,
        data={"cpi_surprise": -0.30},
        source_timestamp=AS_OF + timedelta(days=30),
    )
    with pytest.raises(SystemContaminationHalt):
        detector.guard(result, AS_OF)


def test_historical_without_timestamp_raises_contamination(detector):
    """Un dato que se declara auditable pero no trae con qué auditarlo
    se trata como violación, no como excepción de cortesía."""
    result = CollectorResult(
        source_name="ETFCollector",
        status=DataStatus.HISTORICAL,
        data={"flow_usd": 200_000_000},
        source_timestamp=None,
    )
    with pytest.raises(SystemContaminationHalt):
        detector.guard(result, AS_OF)


def test_contamination_message_names_the_offending_collector(detector):
    result = CollectorResult(
        source_name="OrderBookCollector",
        status=DataStatus.HISTORICAL,
        data={},
        source_timestamp=AS_OF + timedelta(hours=1),
    )
    try:
        detector.guard(result, AS_OF)
        assert False, "debería haber lanzado SystemContaminationHalt"
    except SystemContaminationHalt as e:
        assert "OrderBookCollector" in str(e)
