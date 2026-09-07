"""
HistoricalClock — reloj de simulación para el motor de backtest de Leviathan.

Por qué existe:
El backtest anterior ejecutaba el Kernel como si estuviera en tiempo real,
sin saber en qué día histórico estaba parado. Eso permitía que los
collectors leyeran el estado *actual* del mercado en cada ciclo, en vez
del estado correspondiente a la vela que se estaba simulando — la causa
raíz probable del patrón "729 trades sobre 730 velas" detectado en la
auditoría.

Este módulo implementa el Invariante T.2 (Strict Monotonic Time Progress),
congelado en la Fase 2 del diseño conceptual:

    T.2: para todo i en [1, N], as_of_i > as_of_(i-1)
         (el reloj nunca permanece igual ni retrocede)

El HistoricalClock no tiene lógica propia de avance: es el BacktestEngine
quien decide "ahora estamos en este día" y se lo informa al reloj. El
reloj se limita a validar que ese avance sea válido y a exponer un
snapshot inmutable (ClockContext) para que los collectors lo consuman
sin poder alterar el estado real del reloj.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class ClockRegressionError(Exception):
    """
    Se lanza cuando se intenta mover el reloj a un as_of igual o anterior
    al último confirmado.

    Esto se clasifica como fallo CRITICAL, no recuperable: si el tiempo
    simulado retrocede, cualquier estado acumulado en los collectors
    (medias móviles, ventanas de funding, etc.) queda corrompido y ya no
    se puede confiar en el resto de la corrida. Por eso no se atrapa y se
    sigue adelante — se detiene toda la sesión (HALT total), tal como se
    aprobó en la Fase 2.
    """
    pass


@dataclass(frozen=True)
class ClockContext:
    """
    Snapshot inmutable de un as_of.

    Es lo único que reciben los collectors — nunca una referencia al
    HistoricalClock real. Esto es deliberado: así ningún collector puede,
    ni por error de implementación, llamar a advance() desde adentro y
    alterar el reloj compartido.
    """
    as_of: datetime
    cycle_index: int  # posición en la simulación (0, 1, 2, ...) — útil para logs y auditoría


class HistoricalClock:
    """
    Mantiene el estado del horizonte temporal del backtest y garantiza
    que avance de forma estrictamente monótona.

    Uso típico dentro del BacktestEngine:

        clock = HistoricalClock()
        for i, day in enumerate(df.itertuples()):
            ctx = clock.advance(day.Date, cycle_index=i)
            result = await kernel.run_cycle(symbol="BTC", as_of=ctx)
    """

    def __init__(self) -> None:
        self._last: Optional[datetime] = None
        self._current: Optional[ClockContext] = None

    @property
    def current(self) -> ClockContext:
        if self._current is None:
            raise RuntimeError(
                "HistoricalClock todavía no fue inicializado — "
                "llamá a advance() antes de leer current."
            )
        return self._current

    def advance(self, new_as_of: datetime, cycle_index: int) -> ClockContext:
        """
        Mueve el reloj al siguiente as_of.

        Lanza ClockRegressionError si new_as_of no es estrictamente
        posterior al último as_of confirmado (Invariante T.2).
        """
        if self._last is not None and new_as_of <= self._last:
            raise ClockRegressionError(
                f"Intento de mover el reloj de {self._last} a {new_as_of}. "
                f"El tiempo simulado no puede permanecer igual ni retroceder "
                f"(Invariante T.2). Esto normalmente indica un bug en el "
                f"loop del BacktestEngine o filas desordenadas/duplicadas "
                f"en el dataset fuente."
            )
        self._last = new_as_of
        self._current = ClockContext(as_of=new_as_of, cycle_index=cycle_index)
        return self._current
