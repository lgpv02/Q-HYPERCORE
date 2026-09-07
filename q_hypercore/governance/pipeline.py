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
