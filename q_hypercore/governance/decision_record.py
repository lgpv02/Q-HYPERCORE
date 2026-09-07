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
