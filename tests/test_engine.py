import pytest
from q_hypercore.core.engine import MetaOrchestrator, ProblemPayload, ComputeTarget

@pytest.mark.asyncio
async def test_quantum_routing_thresholds():
    orchestrator = MetaOrchestrator()

    p1 = ProblemPayload(problem_id="T1", complexity_score=8.0, has_quantum_algorithm=True, budget_usd=0.15)
    d1 = await orchestrator.decide_route(p1)
    assert d1.target == ComputeTarget.QUANTUM_HARDWARE

    p2 = ProblemPayload(problem_id="T2", complexity_score=6.0, has_quantum_algorithm=True, budget_usd=0.05)
    d2 = await orchestrator.decide_route(p2)
    assert d2.target == ComputeTarget.QUANTUM_SIMULATOR

    p3 = ProblemPayload(problem_id="T3", complexity_score=4.0, has_quantum_algorithm=True, budget_usd=0.01)
    d3 = await orchestrator.decide_route(p3)
    assert d3.target == ComputeTarget.QUANTUM_INSPIRED

@pytest.mark.asyncio
async def test_classical_and_llm_routing():
    orchestrator = MetaOrchestrator()

    p4 = ProblemPayload(problem_id="T4", complexity_score=7.5, requires_reasoning=True)
    d4 = await orchestrator.decide_route(p4)
    assert d4.target == ComputeTarget.LARGE_REASONING_LLM

    p5 = ProblemPayload(problem_id="T5", complexity_score=2.0, requires_reasoning=False)
    d5 = await orchestrator.decide_route(p5)
    assert d5.target == ComputeTarget.CPU_CLASSIC
