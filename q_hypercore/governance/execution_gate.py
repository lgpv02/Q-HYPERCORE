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
