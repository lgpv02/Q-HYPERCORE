#!/usr/bin/env python3
"""
Conector generico para universos externos.
Creado en esta sesion (no restaurado de ningun zip previo).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseConnector(ABC):
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        self.status = "initialized"
        self.last_error: Optional[str] = None

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        pass

    def disconnect(self):
        self.status = "disconnected"
        print(f"[{self.name}] Desconectado")
