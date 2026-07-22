"""Configuración y adaptador del modelo Gemini para generación."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from dotenv import dotenv_values

from ..configuracion import RAIZ_AGENTE
from .modelos import SalidaLLM


class ProveedorLLM(Protocol):
    """Contrato pequeño para sustituir Gemini durante las pruebas."""

    def generar(
        self,
        instruccion_sistema: str,
        mensaje_usuario: str,
    ) -> SalidaLLM:
        """Genera una salida estructurada a partir del contexto."""


class ErrorConfiguracionLLM(ValueError):
    """Indica que faltan valores para crear el modelo de lenguaje."""


class ErrorLLM(RuntimeError):
    """Indica que el proveedor no pudo generar una respuesta válida."""


@dataclass(frozen=True)
class ConfiguracionLLM:
    """Configuración del LLM sin mostrar la credencial en registros."""

    modelo: str
    clave_api: str = field(repr=False)


ESQUEMA_RESPUESTA = {
    "type": "object",
    "properties": {
        "respuesta": {
            "type": "string",
            "description": "Respuesta breve basada exclusivamente en el contexto.",
        },
        "informacion_encontrada": {
            "type": "boolean",
            "description": (
                "Verdadero solo si el contexto respalda la respuesta solicitada."
            ),
        },
        "fuentes_utilizadas": {
            "type": "array",
            "items": {"type": "integer"},
            "description": (
                "Números de las fuentes del contexto que respaldan la respuesta."
            ),
        },
    },
    "required": [
        "respuesta",
        "informacion_encontrada",
        "fuentes_utilizadas",
    ],
}


def _descripcion_codigo(codigo: int | None, estado: str | None) -> str:
    """Construye una referencia técnica segura sin incluir la respuesta privada."""

    if codigo:
        return f"HTTP {codigo}"
    if estado:
        return f"estado {estado}"
    return "sin código disponible"


def _mensaje_error_api(error: Any, modelo: str) -> str:
    """Traduce errores de Gemini a acciones comprensibles para el usuario."""

    codigo = getattr(error, "code", None)
    estado = str(getattr(error, "status", "") or "").upper()
    referencia = _descripcion_codigo(codigo, estado)

    if codigo == 401 or estado == "UNAUTHENTICATED":
        return (
            f"Gemini rechazó la API key ({referencia}). "
            "Verifica GEMINI_API_KEY."
        )
    if codigo == 403 or estado == "PERMISSION_DENIED":
        return (
            f"La API key no tiene permiso para usar Gemini ({referencia}). "
            "Revisa el proyecto y los permisos asociados a la credencial."
        )
    if codigo == 404 or estado == "NOT_FOUND":
        return (
            f"El modelo '{modelo}' no está disponible para esta credencial "
            f"({referencia}). Revisa LLM_MODEL."
        )
    if codigo == 429 or estado == "RESOURCE_EXHAUSTED":
        return (
            f"Gemini rechazó la consulta por límite de solicitudes o cuota "
            f"agotada ({referencia}). Espera unos minutos y revisa la cuota."
        )
    if codigo in {408, 504} or estado in {"DEADLINE_EXCEEDED", "TIMEOUT"}:
        return (
            f"Gemini superó el tiempo máximo de respuesta ({referencia}). "
            "Intenta nuevamente."
        )
    if codigo == 400 or estado == "INVALID_ARGUMENT":
        return (
            f"La solicitud enviada a Gemini no fue válida ({referencia}). "
            "Revisa LLM_MODEL y el tamaño del contexto recuperado."
        )
    if isinstance(codigo, int) and 500 <= codigo < 600:
        return (
            f"Gemini está temporalmente fuera de servicio ({referencia}). "
            "Intenta nuevamente más tarde."
        )
    return (
        f"Gemini rechazó la solicitud ({referencia}). "
        "Revisa la configuración y vuelve a intentarlo."
    )


class GeminiLLM:
    """Adaptador directo sobre Google Gen AI con respuesta JSON estructurada."""

    def __init__(
        self,
        configuracion: ConfiguracionLLM,
        *,
        cliente: Any | None = None,
    ) -> None:
        from google import genai

        self.configuracion = configuracion
        self.cliente = cliente or genai.Client(api_key=configuracion.clave_api)

    def generar(
        self,
        instruccion_sistema: str,
        mensaje_usuario: str,
    ) -> SalidaLLM:
        """Invoca Gemini y valida la estructura antes de devolverla."""

        from google.genai import types
        from google.genai.errors import APIError

        try:
            respuesta = self.cliente.models.generate_content(
                model=self.configuracion.modelo,
                contents=mensaje_usuario,
                config=types.GenerateContentConfig(
                    system_instruction=instruccion_sistema,
                    response_mime_type="application/json",
                    response_json_schema=ESQUEMA_RESPUESTA,
                    temperature=0.1,
                ),
            )
        except APIError as error:
            raise ErrorLLM(
                _mensaje_error_api(error, self.configuracion.modelo)
            ) from error

        datos = getattr(respuesta, "parsed", None)
        if datos is None:
            try:
                datos = json.loads(respuesta.text or "")
            except (json.JSONDecodeError, TypeError) as error:
                raise ErrorLLM(
                    "Gemini no devolvió una respuesta estructurada válida."
                ) from error
        if not isinstance(datos, dict):
            raise ErrorLLM("Gemini devolvió una estructura inesperada.")

        try:
            return SalidaLLM.desde_datos(datos)
        except ValueError as error:
            raise ErrorLLM(str(error)) from error


def _valores_env(ruta_env: Path) -> dict[str, str]:
    valores_archivo = dotenv_values(ruta_env) if ruta_env.is_file() else {}
    return {
        clave: os.getenv(clave) or str(valores_archivo.get(clave) or "")
        for clave in ("GEMINI_API_KEY", "LLM_MODEL")
    }


def cargar_configuracion_llm(
    *,
    raiz_agente: Path | None = None,
    ruta_env: Path | None = None,
) -> ConfiguracionLLM:
    """Lee los nombres existentes del .env sin exponer la clave de Gemini."""

    raiz = (raiz_agente or RAIZ_AGENTE).resolve()
    archivo_env = ruta_env or (raiz / ".env")
    valores = _valores_env(archivo_env)
    faltantes = [clave for clave, valor in valores.items() if not valor.strip()]
    if faltantes:
        raise ErrorConfiguracionLLM(
            "Faltan variables para el LLM: " + ", ".join(faltantes) + "."
        )
    return ConfiguracionLLM(
        modelo=valores["LLM_MODEL"].strip(),
        clave_api=valores["GEMINI_API_KEY"].strip(),
    )


def crear_proveedor_llm(
    configuracion: ConfiguracionLLM | None = None,
) -> ProveedorLLM:
    """Crea el proveedor configurado sin fijar el modelo en el código."""

    if configuracion is None:
        configuracion = cargar_configuracion_llm()
    try:
        from google import genai  # noqa: F401
    except ImportError as error:
        raise ErrorConfiguracionLLM(
            "Instala las dependencias de Agente/requirements.txt."
        ) from error
    return GeminiLLM(configuracion)
