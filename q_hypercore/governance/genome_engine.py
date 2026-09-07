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
