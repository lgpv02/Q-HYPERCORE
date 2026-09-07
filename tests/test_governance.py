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
