"""
BaseCollector — contrato que deben cumplir todos los collectors del
Kernel (Whale, Liquidation, OI, Funding, ETF, SpotVolume, OrderBook,
Macro) para poder participar de un ciclo de backtest.

La firma de collect() es obligatoria y siempre exige un ClockContext:
no existe una versión de collect() sin él. Esto es intencional — es la
forma de que sea imposible, por diseño, correr un collector "a ciegas"
sin saber en qué momento histórico está parado. Un collector que
implemente esta clase pero no reciba ni use el as_of correctamente no
puede compilar/instanciarse como collector válido del sistema.
"""

from __future__ import annotations
from abc import ABC, abstractmethod

from .historical_clock import ClockContext
from .look_ahead_detector import CollectorResult


class BaseCollector(ABC):
    #: Nombre legible del collector, usado en logs, en CollectorResult
    #: y en el data_audit del DecisionRecord.
    name: str = "BaseCollector"

    @abstractmethod
    def collect(self, ctx: ClockContext) -> CollectorResult:
        """
        Devuelve el estado de esta fuente de datos para ctx.as_of.

        Reglas que toda implementación concreta debe respetar:

        1. Buscar el dato correspondiente a ctx.as_of — nunca "el dato
           más reciente disponible ahora mismo".
        2. Si todavía no existe una fuente histórica real para esta
           fecha, devolver status=UNAVAILABLE. Nunca inventar un valor
           ni usar el dato actual como sustituto silencioso: eso es
           exactamente el bug que esta arquitectura busca eliminar.
        3. Si el dato es un relleno declarado (por ejemplo, macro
           mientras no exista un conector histórico implementado),
           devolver status=STABLE_STUB de forma explícita — nunca
           HISTORICAL. El Gate trata ambos casos de forma distinta
           (ver Fase 2: STABLE_STUB penaliza confianza pero no fuerza
           WAIT; UNAVAILABLE sí lo fuerza).
        4. Incluir siempre source_timestamp cuando status no sea
           UNAVAILABLE, para que LookAheadDetector pueda auditar el
           dato contra el as_of vigente.
        """
        raise NotImplementedError
