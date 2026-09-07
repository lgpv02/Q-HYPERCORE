#!/data/data/com.termux/files/usr/bin/bash
set -e
cd ~/Q-HYPERCORE
mkdir -p q_hypercore/governance tests
touch q_hypercore/governance/__init__.py

cat > q_hypercore/governance/decision_record.py << 'PYEOF'
"""
q_hypercore/governance/decision_record.py

Expediente de señal — dataclass puro, sin dependencias externas (coincide
con el estilo de q_hypercore/core/engine.py en Honor: sin pydantic).

REGLA DURA: este objeto no tiene ningún método que transicione su propio
execution_status. guide_score/confidence son informativos — nunca causan
una transición de estado por sí solos.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ExecutionStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"


@dataclass
class DecisionRecord:
    symbol: str
    guide_score: float
    confidence: float
    macro_context: str = ""
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    as_of: Optional[str] = None
    execution_status: ExecutionStatus = ExecutionStatus.PENDING_REVIEW
    payload_hash: Optional[str] = None

    def __post_init__(self):
        if self.as_of is None:
            self.as_of = self.timestamp

    def to_dict(self) -> dict:
        d = asdict(self)
        d["execution_status"] = self.execution_status.value
        return d

    def compute_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("payload_hash", None)
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
PYEOF

cat > q_hypercore/governance/execution_gate.py << 'PYEOF'
"""
q_hypercore/governance/execution_gate.py

Human-in-the-loop Execution Gate. No ejecuta órdenes reales — solo la
máquina de estados de autorización + auditoría append-only.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, Optional

from q_hypercore.governance.decision_record import DecisionRecord, ExecutionStatus


class GateError(Exception):
    pass


class UnknownOperationError(GateError):
    pass


class InvalidTransitionError(GateError):
    pass


class MissingHumanIdentifierError(GateError):
    pass


class ExecutionGate:
    def __init__(self, audit_log_path: str):
        self._records: Dict[str, DecisionRecord] = {}
        self._audit_log_path = audit_log_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(audit_log_path) or ".", exist_ok=True)

    def _append_audit(self, event: str, record: DecisionRecord, extra: Optional[dict] = None) -> None:
        entry = {
            "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "operation_id": record.operation_id,
            "symbol": record.symbol,
            "guide_score": record.guide_score,
            "confidence": record.confidence,
            "execution_status": record.execution_status.value,
        }
        if extra:
            entry.update(extra)
        with open(self._audit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def submit(self, record: DecisionRecord) -> str:
        with self._lock:
            record.execution_status = ExecutionStatus.PENDING_REVIEW
            self._records[record.operation_id] = record
            self._append_audit("SUBMITTED", record)
            return record.operation_id

    def get(self, operation_id: str) -> DecisionRecord:
        record = self._records.get(operation_id)
        if record is None:
            raise UnknownOperationError(f"operation_id desconocido: {operation_id}")
        return record

    def approve(self, operation_id: str, human_identifier: str, note: str = "") -> DecisionRecord:
        if not human_identifier or not human_identifier.strip():
            raise MissingHumanIdentifierError("No se puede aprobar sin identificar a la persona responsable.")
        with self._lock:
            record = self.get(operation_id)
            if record.execution_status != ExecutionStatus.PENDING_REVIEW:
                raise InvalidTransitionError(
                    f"No se puede aprobar una decisión en estado {record.execution_status.value}."
                )
            record.execution_status = ExecutionStatus.APPROVED
            record.payload_hash = record.compute_hash()
            self._append_audit("APPROVED", record, extra={"approved_by": human_identifier, "note": note})
            return record

    def reject(self, operation_id: str, human_identifier: str, reason: str = "") -> DecisionRecord:
        if not human_identifier or not human_identifier.strip():
            raise MissingHumanIdentifierError("No se puede rechazar sin identificar a la persona responsable.")
        with self._lock:
            record = self.get(operation_id)
            if record.execution_status != ExecutionStatus.PENDING_REVIEW:
                raise InvalidTransitionError(
                    f"No se puede rechazar una decisión en estado {record.execution_status.value}."
                )
            record.execution_status = ExecutionStatus.REJECTED
            self._append_audit("REJECTED", record, extra={"rejected_by": human_identifier, "reason": reason})
            return record

    def mark_executed(self, operation_id: str, execution_reference: str) -> DecisionRecord:
        with self._lock:
            record = self.get(operation_id)
            if record.execution_status != ExecutionStatus.APPROVED:
                raise InvalidTransitionError(
                    f"No se puede marcar como ejecutada una decisión en estado {record.execution_status.value}."
                )
            record.execution_status = ExecutionStatus.EXECUTED
            self._append_audit("EXECUTED", record, extra={"execution_reference": execution_reference})
            return record
PYEOF

cat > q_hypercore/governance/genome_engine.py << 'PYEOF'
"""
q_hypercore/governance/genome_engine.py

Reglas inmutables de veto. No decide aprobar nada — decide si una señal
tiene derecho a llegar a PENDING_REVIEW.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from q_hypercore.governance.decision_record import DecisionRecord


class GenomeViolationError(Exception):
    def __init__(self, violations: List[str]):
        self.violations = violations
        super().__init__("Genome violado: " + "; ".join(violations))


@dataclass(frozen=True)
class GenomeRule:
    name: str
    check: Callable[[DecisionRecord], Optional[str]]


class GenomeEngine:
    def __init__(self, rules: List[GenomeRule]):
        self._rules: Tuple[GenomeRule, ...] = tuple(rules)

    @property
    def rules(self) -> Tuple[GenomeRule, ...]:
        return self._rules

    def evaluate(self, record: DecisionRecord) -> None:
        violations = []
        for rule in self._rules:
            result = rule.check(record)
            if result is not None:
                violations.append(f"{rule.name}: {result}")
        if violations:
            raise GenomeViolationError(violations)


def rule_score_in_valid_range(record: DecisionRecord) -> Optional[str]:
    if not (0.0 <= record.guide_score <= 100.0):
        return f"guide_score fuera de rango [0,100]: {record.guide_score}"
    return None


def rule_confidence_in_valid_range(record: DecisionRecord) -> Optional[str]:
    if not (0.0 <= record.confidence <= 1.0):
        return f"confidence fuera de rango [0,1]: {record.confidence}"
    return None


def rule_symbol_not_empty(record: DecisionRecord) -> Optional[str]:
    if not record.symbol or not record.symbol.strip():
        return "symbol vacío — expediente no identificable"
    return None


def build_default_genome() -> GenomeEngine:
    return GenomeEngine([
        GenomeRule("G.score_range", rule_score_in_valid_range),
        GenomeRule("G.confidence_range", rule_confidence_in_valid_range),
        GenomeRule("G.symbol_required", rule_symbol_not_empty),
    ])
PYEOF

cat > q_hypercore/governance/pipeline.py << 'PYEOF'
"""
q_hypercore/governance/pipeline.py
Une Genome y ExecutionGate en el orden correcto (Opción B: Genome corre
UNA vez, sobre el DecisionRecord ya fusionado, antes del gate).
"""
from __future__ import annotations

from q_hypercore.governance.decision_record import DecisionRecord
from q_hypercore.governance.execution_gate import ExecutionGate
from q_hypercore.governance.genome_engine import GenomeEngine, GenomeViolationError


def submit_with_genome(genome: GenomeEngine, gate: ExecutionGate, record: DecisionRecord) -> str:
    genome.evaluate(record)  # lanza si viola; nada después puede "rescatar" la señal
    return gate.submit(record)
PYEOF

cat > q_hypercore/governance/merger.py << 'PYEOF'
"""
q_hypercore/governance/merger.py
Merger mínimo real: consolida propuestas en un único DecisionRecord.
Si los symbols no coinciden, produce symbol="" a propósito, para que
Genome lo vete en vez de que el Merger arbitre en silencio.
"""
from __future__ import annotations

from typing import Dict, List

from q_hypercore.governance.decision_record import DecisionRecord


class EmptyProposalListError(Exception):
    pass


def merge_proposals(proposals: List[Dict]) -> DecisionRecord:
    if not proposals:
        raise EmptyProposalListError("merge_proposals() recibió una lista vacía de propuestas.")

    symbols = {p["symbol"] for p in proposals}
    merged_symbol = symbols.pop() if len(symbols) == 1 else ""

    avg_score = sum(p["guide_score"] for p in proposals) / len(proposals)
    avg_confidence = sum(p["confidence"] for p in proposals) / len(proposals)
    macro_context = " | ".join(p.get("label", "sin_etiqueta") for p in proposals)

    return DecisionRecord(
        symbol=merged_symbol,
        guide_score=avg_score,
        confidence=avg_confidence,
        macro_context=macro_context,
    )
PYEOF

cat > tests/test_governance.py << 'PYEOF'
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from q_hypercore.governance.decision_record import DecisionRecord, ExecutionStatus
from q_hypercore.governance.execution_gate import (
    ExecutionGate, InvalidTransitionError, MissingHumanIdentifierError, UnknownOperationError,
)
from q_hypercore.governance.genome_engine import GenomeViolationError, build_default_genome
from q_hypercore.governance.merger import EmptyProposalListError, merge_proposals
from q_hypercore.governance.pipeline import submit_with_genome


@pytest.fixture
def genome():
    return build_default_genome()


@pytest.fixture
def gate(tmp_path):
    return ExecutionGate(audit_log_path=str(tmp_path / "audit.log"))


def test_submit_with_max_score_lands_in_pending_review_not_approved(gate):
    record = DecisionRecord(symbol="BTCUSDT", guide_score=100.0, confidence=1.0)
    op_id = gate.submit(record)
    stored = gate.get(op_id)
    assert stored.execution_status == ExecutionStatus.PENDING_REVIEW


def test_approve_requires_non_empty_human_identifier(gate):
    record = DecisionRecord(symbol="BTCUSDT", guide_score=99.9, confidence=0.99)
    op_id = gate.submit(record)
    with pytest.raises(MissingHumanIdentifierError):
        gate.approve(op_id, human_identifier="")


def test_explicit_human_approval_moves_to_approved(gate):
    record = DecisionRecord(symbol="BTCUSDT", guide_score=85.0, confidence=0.8)
    op_id = gate.submit(record)
    approved = gate.approve(op_id, human_identifier="perdomo")
    assert approved.execution_status == ExecutionStatus.APPROVED
    assert approved.payload_hash is not None


def test_cannot_approve_twice(gate):
    record = DecisionRecord(symbol="BTCUSDT", guide_score=85.0, confidence=0.8)
    op_id = gate.submit(record)
    gate.approve(op_id, human_identifier="perdomo")
    with pytest.raises(InvalidTransitionError):
        gate.approve(op_id, human_identifier="perdomo")


def test_genome_violation_never_reaches_pending_review(genome, gate):
    bad_record = DecisionRecord(symbol="BTCUSDT", guide_score=999.0, confidence=0.8)
    with pytest.raises(GenomeViolationError):
        submit_with_genome(genome, gate, bad_record)
    with pytest.raises(UnknownOperationError):
        gate.get(bad_record.operation_id)


def test_genome_valid_record_reaches_pending_review(genome, gate):
    good_record = DecisionRecord(symbol="BTCUSDT", guide_score=85.0, confidence=0.8)
    op_id = submit_with_genome(genome, gate, good_record)
    assert gate.get(op_id).execution_status == ExecutionStatus.PENDING_REVIEW


def test_merger_to_genome_to_gate_happy_path(genome, gate):
    proposals = [
        {"symbol": "BTCUSDT", "guide_score": 80.0, "confidence": 0.80, "label": "strategy:BUY"},
        {"symbol": "BTCUSDT", "guide_score": 84.0, "confidence": 0.85, "label": "risk:OK"},
    ]
    record = merge_proposals(proposals)
    op_id = submit_with_genome(genome, gate, record)
    assert gate.get(op_id).execution_status == ExecutionStatus.PENDING_REVIEW


def test_merger_conflicting_symbols_produces_empty_symbol_and_genome_vetoes(genome, gate):
    proposals = [
        {"symbol": "BTCUSDT", "guide_score": 80.0, "confidence": 0.80, "label": "strategy:BUY"},
        {"symbol": "ETHUSDT", "guide_score": 84.0, "confidence": 0.85, "label": "risk:OK"},
    ]
    record = merge_proposals(proposals)
    assert record.symbol == ""
    with pytest.raises(GenomeViolationError):
        submit_with_genome(genome, gate, record)


def test_merger_raises_on_empty_proposal_list():
    with pytest.raises(EmptyProposalListError):
        merge_proposals([])
PYEOF

echo "=== Archivos creados en ~/Q-HYPERCORE/q_hypercore/governance/ y tests/test_governance.py ==="
find q_hypercore/governance tests/test_governance.py -type f
echo ""
echo "=== Corriendo tests ==="
python3 -m pytest tests/test_governance.py -v
