"""Recuperación semántica de fragmentos previamente indexados."""

from .contexto import ensamblar_contexto
from .modelos import FiltrosRecuperacion, FragmentoRecuperado
from .recuperador import ErrorRecuperacion, recuperar_fragmentos

__all__ = [
    "ErrorRecuperacion",
    "FiltrosRecuperacion",
    "FragmentoRecuperado",
    "ensamblar_contexto",
    "recuperar_fragmentos",
]
