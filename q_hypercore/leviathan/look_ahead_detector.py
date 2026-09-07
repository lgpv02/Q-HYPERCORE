"""
LookAheadDetector — guardián centralizado de los Invariantes T.1 y T.3.

Por qué vive en el Kernel y no dentro de cada collector (decisión
tomada en la Fase 2): delegar la validación a cada collector individual
rompe el principio de "single point of truth". Cualquier collector nuevo
que se agregue en el futuro podría olvidarse de validar, y el bug de
look-ahead volvería a colarse silenciosamente — como probablemente pasó
en la corrida que dio 729 trades sobre 730 velas. Al envolver la llamada
a collect() desde un único lugar, la garantía es estructural: no depende
de la disciplina de cada implementación nueva.

    T.1 (Temporal Causal Constraint):
        para todo dato d, Timestamp(d) <= as_of
        => status en {HISTORICAL, STABLE_STUB, UNAVAILABLE}
        si no se cumple => SYSTEM_CONTAMINATION_HALT

    T.3 (Kernel Isolation of Leakage):
        ninguna respuesta de collector entra al bus de evaluación sin
        pasar primero por este detector.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class DataStatus(str, Enum):
    HISTORICAL = "HISTORICAL"      # dato real, verificado, timestamp <= as_of
    STABLE_STUB = "STABLE_STUB"    # relleno declarado explícitamente (ej. macro sin conector histórico todavía)
    UNAVAILABLE = "UNAVAILABLE"    # no hay dato para este as_of; nunca se inventa un sustituto


class SystemContaminationHalt(Exception):
    """
    Fallo CRITICAL, no recuperable dentro del ciclo.

    Se lanza cuando un collector devuelve un dato con timestamp
    posterior al as_of vigente, o declara HISTORICAL/STABLE_STUB sin
    poder probar su origen temporal. No tiene sentido "saltear ese día y
    seguir": si un collector filtró datos futuros una vez, es señal de
    un problema estructural (por ejemplo, un collector que sigue
    apuntando a la API en vivo en vez de a la fuente histórica), y el
    resto de la corrida ya no es confiable. Por eso aborta todo
    BacktestEngine.run(), no solo el ciclo actual — tal como se aprobó
    en la Fase 2.
    """
    pass


@dataclass(frozen=True)
class CollectorResult:
    """
    Contrato de salida obligatorio para TODO collector, histórico o no.
    """
    source_name: str                        # ej. "WhaleCollector", "OICollector"
    status: DataStatus
    data: Optional[dict]
    source_timestamp: Optional[datetime]    # None es válido únicamente si status == UNAVAILABLE


class LookAheadDetector:
    """
    Middleware que envuelve cada llamada a collector.collect(ctx) dentro
    del Kernel. Ver Invariante T.3: ningún CollectorResult debería llegar
    al bus de evaluación sin pasar por guard() primero.
    """

    def guard(self, result: CollectorResult, as_of: datetime) -> CollectorResult:
        """
        Valida un CollectorResult contra el as_of vigente del ciclo.

        - UNAVAILABLE: no hay timestamp que chequear, siempre pasa. Es
          preferible que el sistema declare "no sé" a que rellene con
          un dato disfrazado de histórico.
        - HISTORICAL / STABLE_STUB: debe traer source_timestamp, y ese
          timestamp debe ser <= as_of. Si cualquiera de las dos
          condiciones falla, es contaminación y se aborta todo el
          backtest.
        """
        if result.status == DataStatus.UNAVAILABLE:
            return result

        if result.source_timestamp is None:
            raise SystemContaminationHalt(
                f"{result.source_name} devolvió status={result.status.value} "
                f"sin source_timestamp. Un dato declarado HISTORICAL o "
                f"STABLE_STUB debe traer su timestamp de origen para poder "
                f"auditarse — si no lo tiene, se trata como violación del "
                f"Invariante T.1."
            )

        if result.source_timestamp > as_of:
            raise SystemContaminationHalt(
                f"LOOK-AHEAD DETECTADO en {result.source_name}: el dato "
                f"tiene timestamp {result.source_timestamp}, posterior al "
                f"as_of de la simulación ({as_of}). El collector está "
                f"leyendo datos del futuro respecto al momento que se "
                f"está simulando (violación del Invariante T.1)."
            )

        return result
