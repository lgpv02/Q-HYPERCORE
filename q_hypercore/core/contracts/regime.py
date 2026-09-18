from datetime import datetime
from enum import Enum
from typing import Dict, List
from pydantic import BaseModel, Field

class MarketRegimeType(str, Enum):
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    HIGH_VOLATILITY_RANGE = "HIGH_VOLATILITY_RANGE"
    LOW_VOLATILITY_RANGE = "LOW_VOLATILITY_RANGE"
    LIQUIDITY_CRUNCH = "LIQUIDITY_CRUNCH"
    UNKNOWN_HIGH_RISK = "UNKNOWN_HIGH_RISK"  # Fallback por degradación de datos

class RegimeDimensions(BaseModel):
    """
    Las 7 Dimensiones del Estado de Régimen según la especificación Tiburón/Leviathan.
    """
    inflation: float = Field(0.0, ge=-1.0, le=1.0, description="Presión inflacionaria (-1 pasiva, +1 alta)")
    growth: float = Field(0.0, ge=-1.0, le=1.0, description="Crecimiento económico")
    employment: float = Field(0.0, ge=-1.0, le=1.0, description="Salud del mercado laboral")
    fed_stance: float = Field(0.0, ge=-1.0, le=1.0, description="Postura de política monetaria (-1 dovish, +1 hawkish)")
    yields_pressure: float = Field(0.0, ge=-1.0, le=1.0, description="Presión en rendimientos de bonos")
    usd_bias: float = Field(0.0, ge=-1.0, le=1.0, description="Fuerza/sesgo del USD")
    risk_appetite: float = Field(0.0, ge=-1.0, le=1.0, description="Apetito por el riesgo global")

    class Config:
        frozen = True

class MarketRegimeSnapshot(BaseModel):
    """
    Snapshot completo de régimen probabilístico emitido por el Market Context Engine.
    """
    snapshot_id: str = Field(..., description="Hash/ID único del snapshot")
    as_of_timestamp: datetime = Field(..., description="Timestamp de congelamiento de información (HistoricalClock)")
    primary_regime: MarketRegimeType = Field(..., description="Régimen dominante detectado")
    regime_probabilities: Dict[MarketRegimeType, float] = Field(..., description="Distribución de probabilidad por régimen")
    dimensions: RegimeDimensions = Field(..., description="Estado de las 7 dimensiones con decay")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Gráfico/Nivel de confianza en el diagnóstico")
    automatic_trade_allowed: bool = Field(False, description="Doctrina dura: SIEMPRE False en este módulo")
    source_event_ids: List[str] = Field(default_factory=list, description="Lista de MacroEvents que compusieron este snapshot")

    class Config:
        frozen = True
