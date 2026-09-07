"""
q_hypercore/governance/historical_clock.py

Invariantes de Causalidad Temporal.

T.1 (Causalidad): ningún collector puede entregar datos con timestamp
    posterior a as_of. Violación -> LookAheadContaminationError.
T.2 (Monotonía): el reloj no puede retroceder ni quedarse igual;
    as_of_i debe ser estrictamente mayor que as_of_(i-1).
    Violación -> ClockRegressionError.
T.3 (Aislamiento del Kernel): el LookAheadDetector es middleware
    OBLIGATORIO entre cualquier collector y el resto del sistema.

Por decisión de diseño confirmada (D2.2 = B): este módulo NO se inyecta
en GenomeEngine. Se mantienen deliberadamente separados. La orquestación
de orden entre ambos vive en integration.py, no aquí ni en genome_engine.py.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict


class SystemContaminationHalt(Exception):
    """Excepción base — cualquier violación de causalidad temporal detiene el flujo."""


class LookAheadContaminationError(SystemContaminationHalt):
    """T.1: un collector intentó entregar datos con timestamp futuro respecto a as_of."""


class ClockRegressionError(SystemContaminationHalt):
    """T.2: se intentó mover as_of hacia atrás, o dejarlo igual."""


class HistoricalClock:
    """Reloj monotónico único de la sesión de backtest/ejecución."""

    def __init__(self, initial_as_of: datetime):
        self._as_of = initial_as_of

    @property
    def as_of(self) -> datetime:
        return self._as_of

    def advance_to(self, new_as_of: datetime) -> None:
        if new_as_of <= self._as_of:
            raise ClockRegressionError(
                f"Intento de mover el reloj de {self._as_of.isoformat()} a "
                f"{new_as_of.isoformat()} — el tiempo no puede retroceder ni quedarse igual."
            )
        self._as_of = new_as_of

    def validate_timestamp(self, data_timestamp: datetime, source: str = "unknown") -> None:
        if data_timestamp > self._as_of:
            raise LookAheadContaminationError(
                f"Collector '{source}' intentó entregar datos con timestamp "
                f"{data_timestamp.isoformat()}, posterior a as_of={self._as_of.isoformat()}. "
                f"Look-ahead bias detectado — HALT."
            )


class LookAheadDetector:
    def __init__(self, clock: HistoricalClock, collector: Callable[..., Dict[str, Any]], source_name: str):
        self._clock = clock
        self._collector = collector
        self._source_name = source_name

    def fetch(self, *args, **kwargs) -> Dict[str, Any]:
        data = self._collector(*args, **kwargs)
        if "timestamp" not in data:
            raise ValueError(f"El collector '{self._source_name}' no devolvió campo 'timestamp'; no auditable.")
        self._clock.validate_timestamp(data["timestamp"], source=self._source_name)
        return data
