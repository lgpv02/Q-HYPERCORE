from dataclasses import dataclass
from enum import Enum


class ComputeTarget(str, Enum):
    QUANTUM_HARDWARE = "QUANTUM_HARDWARE"
    QUANTUM_SIMULATOR = "QUANTUM_SIMULATOR"
    QUANTUM_INSPIRED = "QUANTUM_INSPIRED"
    LARGE_REASONING_LLM = "LARGE_REASONING_LLM"
    CPU_CLASSIC = "CPU_CLASSIC"


@dataclass
class ProblemPayload:
    problem_id: str
    complexity_score: float
    has_quantum_algorithm: bool = False
    requires_reasoning: bool = False
    budget_usd: float = 0.0


@dataclass
class RoutingDecision:
    problem_id: str
    target: ComputeTarget
    justification: str


class MetaOrchestrator:
    async def decide_route(self, payload: ProblemPayload) -> RoutingDecision:
        if payload.has_quantum_algorithm:
            if payload.complexity_score > 7.5 and payload.budget_usd >= 0.10:
                return RoutingDecision(
                    problem_id=payload.problem_id,
                    target=ComputeTarget.QUANTUM_HARDWARE,
                    justification="complexity>7.5, algoritmo cuantico disponible, presupuesto>=0.10",
                )
            if payload.complexity_score > 5.0 and payload.budget_usd >= 0.03:
                return RoutingDecision(
                    problem_id=payload.problem_id,
                    target=ComputeTarget.QUANTUM_SIMULATOR,
                    justification="complexity>5.0, algoritmo cuantico disponible, presupuesto>=0.03",
                )
            return RoutingDecision(
                problem_id=payload.problem_id,
                target=ComputeTarget.QUANTUM_INSPIRED,
                justification="algoritmo cuantico disponible pero complexity o presupuesto insuficiente",
            )

        if payload.requires_reasoning and payload.complexity_score > 6.0:
            return RoutingDecision(
                problem_id=payload.problem_id,
                target=ComputeTarget.LARGE_REASONING_LLM,
                justification="requiere razonamiento y complexity>6.0",
            )

        return RoutingDecision(
            problem_id=payload.problem_id,
            target=ComputeTarget.CPU_CLASSIC,
            justification="fallback clasico por baja complexity o sin requerimiento de razonamiento",
        )
