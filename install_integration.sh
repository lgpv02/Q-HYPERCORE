#!/data/data/com.termux/files/usr/bin/bash
set -e
cd ~/Q-HYPERCORE
mkdir -p q_hypercore/governance tests

cat > q_hypercore/governance/historical_clock.py << 'PYEOF'
"""
q_hypercore/governance/historical_clock.py

Invariantes de Causalidad Temporal.

T.1 (Causalidad): ningún collector puede entregar datos con timestamp
    posterior a as_of. Violación -> LookAheadContaminationError.
T.2 (Monotonía): el reloj no puede retroceder ni quedarse igual;
    as_of_i debe ser estrictamente mayor que as_of_(i-1).
    Violación -> ClockRegressionError.
T.3 (Aislamiento del Kernel): el LookAheadDetector es middleware
    OBLIGATORIO entre cualquier collector y el resto del sistema.

Por decisión de diseño confirmada (D2.2 = B): este módulo NO se inyecta
en GenomeEngine. Se mantienen deliberadamente separados. La orquestación
de orden entre ambos vive en integration.py, no aquí ni en genome_engine.py.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict


class SystemContaminationHalt(Exception):
    """Excepción base — cualquier violación de causalidad temporal detiene el flujo."""


class LookAheadContaminationError(SystemContaminationHalt):
    """T.1: un collector intentó entregar datos con timestamp futuro respecto a as_of."""


class ClockRegressionError(SystemContaminationHalt):
    """T.2: se intentó mover as_of hacia atrás, o dejarlo igual."""


class HistoricalClock:
    """Reloj monotónico único de la sesión de backtest/ejecución."""

    def __init__(self, initial_as_of: datetime):
        self._as_of = initial_as_of

    @property
    def as_of(self) -> datetime:
        return self._as_of

    def advance_to(self, new_as_of: datetime) -> None:
        if new_as_of <= self._as_of:
            raise ClockRegressionError(
                f"Intento de mover el reloj de {self._as_of.isoformat()} a "
                f"{new_as_of.isoformat()} — el tiempo no puede retroceder ni quedarse igual."
            )
        self._as_of = new_as_of

    def validate_timestamp(self, data_timestamp: datetime, source: str = "unknown") -> None:
        if data_timestamp > self._as_of:
            raise LookAheadContaminationError(
                f"Collector '{source}' intentó entregar datos con timestamp "
                f"{data_timestamp.isoformat()}, posterior a as_of={self._as_of.isoformat()}. "
                f"Look-ahead bias detectado — HALT."
            )


class LookAheadDetector:
    def __init__(self, clock: HistoricalClock, collector: Callable[..., Dict[str, Any]], source_name: str):
        self._clock = clock
        self._collector = collector
        self._source_name = source_name

    def fetch(self, *args, **kwargs) -> Dict[str, Any]:
        data = self._collector(*args, **kwargs)
        if "timestamp" not in data:
            raise ValueError(f"El collector '{self._source_name}' no devolvió campo 'timestamp'; no auditable.")
        self._clock.validate_timestamp(data["timestamp"], source=self._source_name)
        return data
PYEOF

cat > q_hypercore/governance/integration.py << 'PYEOF'
"""
q_hypercore/governance/integration.py

Orquesta el flujo completo E2E, manteniendo Genome y HistoricalClock
DELIBERADAMENTE separados (decisión confirmada D2.2 = B):

    proposals -> Merger.merge_proposals() -> DecisionRecord
              -> HistoricalClock.validate_timestamp()   [chequeo temporal, independiente]
              -> GenomeEngine.evaluate()                [chequeo de negocio, independiente]
              -> ExecutionGate.submit()

Los dos chequeos (temporal y de negocio) son secuenciales pero no se
conocen entre sí — ninguno depende del otro para funcionar. Si cualquiera
de los dos falla, la operación NUNCA llega al gate.

Esto es intencional: si mañana se decide que Genome SÍ debe conocer el
reloj (D2.2 = A), ese sería un cambio de diseño explícito y aislado a
genome_engine.py — no algo que integration.py deba forzar por su cuenta.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from q_hypercore.governance.decision_record import DecisionRecord
from q_hypercore.governance.execution_gate import ExecutionGate
from q_hypercore.governance.genome_engine import GenomeEngine, GenomeViolationError
from q_hypercore.governance.historical_clock import HistoricalClock, SystemContaminationHalt
from q_hypercore.governance.merger import merge_proposals


def submit_e2e(
    proposals: List[Dict],
    genome: GenomeEngine,
    gate: ExecutionGate,
    clock: HistoricalClock,
    record_timestamp: Optional[datetime] = None,
) -> str:
    """
    Punto de entrada único E2E. Orden fijo, no configurable desde fuera:
        1. Merger fusiona las propuestas en un DecisionRecord.
        2. HistoricalClock valida causalidad (si se provee record_timestamp).
        3. GenomeEngine valida reglas de negocio.
        4. ExecutionGate.submit() — SIEMPRE aterriza en PENDING_REVIEW.

    Si el paso 2 o el paso 3 lanzan, el paso 4 NUNCA se ejecuta — no hay
    try/except aquí que trague la excepción y someta la señal de todos modos.
    """
    record = merge_proposals(proposals)

    if record_timestamp is not None:
        clock.validate_timestamp(record_timestamp, source="integration.submit_e2e")

    genome.evaluate(record)  # lanza GenomeViolationError si viola; nada la rescata

    return gate.submit(record)
PYEOF

cat > tests/test_integration_e2e.py << 'PYEOF'
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
PYEOF

echo "=== Archivos nuevos creados ==="
find q_hypercore/governance/historical_clock.py q_hypercore/governance/integration.py tests/test_integration_e2e.py -type f
echo ""
echo "=== Corriendo TODA la suite de governance ==="
python3 -m pytest tests/test_governance.py tests/test_integration_e2e.py -v
