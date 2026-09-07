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
