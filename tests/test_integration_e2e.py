import os
import sys
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from q_hypercore.governance.decision_record import ExecutionStatus
from q_hypercore.governance.execution_gate import ExecutionGate, UnknownOperationError
from q_hypercore.governance.genome_engine import GenomeViolationError, build_default_genome
from q_hypercore.governance.historical_clock import HistoricalClock, LookAheadContaminationError
from q_hypercore.governance.integration import submit_e2e

T0 = datetime(2026, 9, 6, 12, 0, 0)


@pytest.fixture
def genome():
    return build_default_genome()


@pytest.fixture
def gate(tmp_path):
    return ExecutionGate(audit_log_path=str(tmp_path / "audit.log"))


@pytest.fixture
def clock():
    return HistoricalClock(initial_as_of=T0)


def _good_proposals():
    return [
        {"symbol": "BTCUSDT", "guide_score": 80.0, "confidence": 0.80, "label": "strategy:BUY"},
        {"symbol": "BTCUSDT", "guide_score": 84.0, "confidence": 0.85, "label": "risk:OK"},
    ]


def test_e2e_happy_path_reaches_pending_review(genome, gate, clock):
    op_id = submit_e2e(_good_proposals(), genome, gate, clock, record_timestamp=T0 - timedelta(minutes=1))
    assert gate.get(op_id).execution_status == ExecutionStatus.PENDING_REVIEW


def test_e2e_future_timestamp_blocked_by_clock_before_genome_even_runs(genome, gate, clock):
    """
    Caso central: un timestamp del futuro debe ser bloqueado por el reloj,
    y la operación jamás debe llegar al gate — aunque Genome nunca objetaría
    nada de estas propuestas (son válidas en score/confidence/symbol).
    """
    future_ts = T0 + timedelta(hours=1)
    with pytest.raises(LookAheadContaminationError):
        submit_e2e(_good_proposals(), genome, gate, clock, record_timestamp=future_ts)


def test_e2e_genome_violation_still_blocks_even_with_valid_timestamp(genome, gate, clock):
    bad_proposals = [
        {"symbol": "BTCUSDT", "guide_score": 999.0, "confidence": 0.9, "label": "strategy:BAD"},
    ]
    with pytest.raises(GenomeViolationError):
        submit_e2e(bad_proposals, genome, gate, clock, record_timestamp=T0 - timedelta(minutes=1))


def test_e2e_without_timestamp_skips_clock_check_and_still_runs_genome(genome, gate, clock):
    """Si no se provee record_timestamp, el chequeo de reloj se omite (no es obligatorio)."""
    op_id = submit_e2e(_good_proposals(), genome, gate, clock, record_timestamp=None)
    assert gate.get(op_id).execution_status == ExecutionStatus.PENDING_REVIEW


# --- Prueba adversarial: romper el orden a propósito (Genome antes que Clock) ---
def test_adversarial_wrong_order_would_let_future_data_through_genome_first(genome, gate, clock):
    """
    Este test documenta POR QUÉ el orden importa: si alguien invirtiera el
    orden (Genome antes que Clock) en una implementación alternativa, una
    señal con timestamp futuro pero campos de negocio válidos pasaría
    Genome sin problema. Aquí simulamos ese camino incorrecto directamente
    (sin pasar por submit_e2e) para probar que SIN el chequeo de reloj,
    Genome solo no la habría detectado — confirmando que integration.py
    necesita el paso de clock.validate_timestamp() explícito.
    """
    from q_hypercore.governance.merger import merge_proposals
    record = merge_proposals(_good_proposals())
    genome.evaluate(record)  # no lanza — Genome no sabe nada de tiempo, por diseño (D2.2=B)
    # Sin el chequeo de reloj, esta señal futura habría llegado limpia hasta aquí.
    # Esto confirma que integration.py, no genome_engine.py, es responsable del orden.
    future_ts = T0 + timedelta(hours=1)
    with pytest.raises(LookAheadContaminationError):
        clock.validate_timestamp(future_ts, source="adversarial_check")
