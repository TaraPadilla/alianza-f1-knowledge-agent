"""Generación de respuestas fundamentadas en fragmentos recuperados."""

from .generador import FALLBACK_SIN_INFORMACION, ErrorGeneracion, generar_respuesta
from .modelos import RespuestaGenerada, SalidaLLM
from .proveedor_llm import (
    ConfiguracionLLM,
    ErrorConfiguracionLLM,
    ErrorLLM,
    GeminiLLM,
    ProveedorLLM,
    ResultadoPruebaModelo,
    cargar_configuracion_llm,
    crear_proveedor_llm,
    probar_modelo,
)

__all__ = [
    "ConfiguracionLLM",
    "ErrorConfiguracionLLM",
    "ErrorGeneracion",
    "ErrorLLM",
    "FALLBACK_SIN_INFORMACION",
    "GeminiLLM",
    "ProveedorLLM",
    "ResultadoPruebaModelo",
    "RespuestaGenerada",
    "SalidaLLM",
    "cargar_configuracion_llm",
    "crear_proveedor_llm",
    "probar_modelo",
    "generar_respuesta",
]
