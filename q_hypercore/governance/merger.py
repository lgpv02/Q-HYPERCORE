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
