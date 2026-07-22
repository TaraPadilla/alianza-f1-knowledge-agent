"""Configuración y creación del proveedor de embeddings."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from dotenv import dotenv_values

from ..configuracion import RAIZ_AGENTE


class ProveedorEmbeddings(Protocol):
    """Contrato mínimo para poder sustituir Gemini en pruebas o configuración."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Genera un vector para cada documento."""

    def embed_query(self, text: str) -> list[float]:
        """Genera un vector para una consulta futura."""


class ErrorConfiguracionEmbeddings(ValueError):
    """Indica que falta o es inválida la configuración de embeddings."""


class ErrorEmbeddings(RuntimeError):
    """Indica que el proveedor no pudo generar los embeddings solicitados."""


class ErrorLimiteEmbeddings(ErrorEmbeddings):
    """Indica que Gemini agotó los reintentos permitidos por cuota."""


@dataclass(frozen=True)
class ConfiguracionEmbeddings:
    """Configuración validada del proveedor y el almacenamiento vectorial."""

    modelo: str
    dimensiones: int
    directorio_vectorial: Path
    clave_api: str = field(repr=False)


class GeminiEmbeddings:
    """Adaptador pequeño sobre Google Gen AI para documentos y consultas."""

    def __init__(
        self,
        configuracion: ConfiguracionEmbeddings,
        *,
        cliente: Any | None = None,
        max_reintentos_429: int = 2,
        espera_maxima: float = 45.0,
        dormir=time.sleep,
    ) -> None:
        if max_reintentos_429 < 0:
            raise ErrorConfiguracionEmbeddings(
                "max_reintentos_429 no puede ser negativo."
            )
        if espera_maxima <= 0:
            raise ErrorConfiguracionEmbeddings(
                "espera_maxima debe ser mayor que cero."
            )

        from google import genai

        self.configuracion = configuracion
        self.cliente = cliente or genai.Client(api_key=configuracion.clave_api)
        self.max_reintentos_429 = max_reintentos_429
        self.espera_maxima = espera_maxima
        self._dormir = dormir

    @property
    def _es_embedding_2(self) -> bool:
        return "gemini-embedding-2" in self.configuracion.modelo.casefold()

    def _configuracion_solicitud(self, tipo_tarea: str):
        from google.genai import types

        parametros: dict[str, str | int] = {
            "output_dimensionality": self.configuracion.dimensiones,
        }
        # Embedding 2 usa instrucciones en el texto; Embedding 1 usa task_type.
        if not self._es_embedding_2:
            parametros["task_type"] = tipo_tarea
        return types.EmbedContentConfig(**parametros)

    def _preparar_documento(self, texto: str) -> str:
        if self._es_embedding_2:
            return f"title: none | text: {texto}"
        return texto

    def _preparar_consulta(self, texto: str) -> str:
        if self._es_embedding_2:
            return f"task: search result | query: {texto}"
        return texto

    @staticmethod
    def _segundos_reintento(error: Exception) -> float:
        """Obtiene el tiempo de reintento sugerido por Gemini."""

        detalles = getattr(error, "details", {})
        if isinstance(detalles, dict):
            for detalle in detalles.get("error", {}).get("details", []):
                espera = detalle.get("retryDelay")
                if isinstance(espera, str) and espera.endswith("s"):
                    try:
                        return max(0.0, float(espera[:-1]))
                    except ValueError:
                        pass

        coincidencia = re.search(r"retry in ([\d.]+)s", str(error), re.IGNORECASE)
        if coincidencia:
            return max(0.0, float(coincidencia.group(1)))
        return 30.0

    def _solicitar_embeddings(self, *, contents, tipo_tarea: str):
        """Reintenta solo el lote limitado, conservando los lotes anteriores."""

        from google.genai.errors import ClientError

        total_intentos = self.max_reintentos_429 + 1
        for intento in range(total_intentos):
            try:
                return self.cliente.models.embed_content(
                    model=self.configuracion.modelo,
                    contents=contents,
                    config=self._configuracion_solicitud(tipo_tarea),
                )
            except ClientError as error:
                if error.code != 429:
                    raise ErrorEmbeddings(
                        f"Gemini rechazó la solicitud de embeddings: {error.code}."
                    ) from error
                if intento == total_intentos - 1:
                    raise ErrorLimiteEmbeddings(
                        "Gemini mantuvo el límite 429 después de "
                        f"{self.max_reintentos_429} reintentos."
                    ) from error

                espera = self._segundos_reintento(error)
                if espera > self.espera_maxima:
                    raise ErrorLimiteEmbeddings(
                        f"Gemini solicitó esperar {espera:.1f} segundos, "
                        f"superando el máximo permitido de {self.espera_maxima:.1f}."
                    ) from error
                self._dormir(espera)

        raise RuntimeError("No fue posible generar los embeddings.")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Genera embeddings por lotes, uno por cada fragmento recibido."""

        from google.genai import types

        resultado: list[list[float]] = []
        for inicio in range(0, len(texts), 100):
            lote = texts[inicio : inicio + 100]
            contenidos = [
                types.Content(
                    role="user",
                    parts=[types.Part(text=self._preparar_documento(texto))],
                )
                for texto in lote
            ]
            respuesta = self._solicitar_embeddings(
                contents=contenidos,
                tipo_tarea="RETRIEVAL_DOCUMENT",
            )
            embeddings = respuesta.embeddings or []
            resultado.extend([list(embedding.values or []) for embedding in embeddings])

        if len(resultado) != len(texts):
            raise RuntimeError(
                "Gemini no devolvió un embedding por cada fragmento enviado."
            )
        return resultado

    def embed_query(self, text: str) -> list[float]:
        """Queda disponible para la futura fase de recuperación."""

        respuesta = self._solicitar_embeddings(
            contents=self._preparar_consulta(text),
            tipo_tarea="RETRIEVAL_QUERY",
        )
        embeddings = respuesta.embeddings or []
        if len(embeddings) != 1:
            raise RuntimeError("Gemini no devolvió el embedding de la consulta.")
        return list(embeddings[0].values or [])


def _valores_env(ruta_env: Path) -> dict[str, str]:
    """Combina el archivo .env con el entorno sin exponer valores sensibles."""

    valores_archivo = dotenv_values(ruta_env) if ruta_env.is_file() else {}
    claves = (
        "GEMINI_API_KEY",
        "EMBEDDING_MODEL",
        "EMBEDDING_DIMENSIONS",
        "VECTORSTORE_DIR",
    )
    return {
        clave: os.getenv(clave) or str(valores_archivo.get(clave) or "")
        for clave in claves
    }


def cargar_configuracion_embeddings(
    *,
    raiz_agente: Path | None = None,
    ruta_env: Path | None = None,
) -> ConfiguracionEmbeddings:
    """Carga las variables existentes y valida que el índice sea portable."""

    raiz = (raiz_agente or RAIZ_AGENTE).resolve()
    archivo_env = ruta_env or (raiz / ".env")
    valores = _valores_env(archivo_env)

    faltantes = [clave for clave, valor in valores.items() if not valor.strip()]
    if faltantes:
        raise ErrorConfiguracionEmbeddings(
            "Faltan variables para embeddings: " + ", ".join(faltantes) + "."
        )

    try:
        dimensiones = int(valores["EMBEDDING_DIMENSIONS"])
    except ValueError as error:
        raise ErrorConfiguracionEmbeddings(
            "EMBEDDING_DIMENSIONS debe ser un número entero."
        ) from error
    if dimensiones <= 0:
        raise ErrorConfiguracionEmbeddings(
            "EMBEDDING_DIMENSIONS debe ser mayor que cero."
        )

    ruta_configurada = Path(valores["VECTORSTORE_DIR"])
    if ruta_configurada.is_absolute():
        raise ErrorConfiguracionEmbeddings(
            "VECTORSTORE_DIR debe ser una ruta relativa dentro de Agente."
        )

    directorio_vectorial = (raiz / ruta_configurada).resolve()
    if not directorio_vectorial.is_relative_to(raiz):
        raise ErrorConfiguracionEmbeddings(
            "VECTORSTORE_DIR no puede salir de la carpeta Agente."
        )

    return ConfiguracionEmbeddings(
        modelo=valores["EMBEDDING_MODEL"].strip(),
        dimensiones=dimensiones,
        directorio_vectorial=directorio_vectorial,
        clave_api=valores["GEMINI_API_KEY"].strip(),
    )


def crear_proveedor_embeddings(
    configuracion: ConfiguracionEmbeddings | None = None,
    *,
    max_reintentos_429: int = 2,
    espera_maxima: float = 45.0,
) -> ProveedorEmbeddings:
    """Crea Gemini usando exclusivamente los valores definidos en el .env."""

    if configuracion is None:
        configuracion = cargar_configuracion_embeddings()

    try:
        from google import genai  # noqa: F401
    except ImportError as error:
        raise ErrorConfiguracionEmbeddings(
            "Instala las dependencias de Agente/requirements.txt."
        ) from error

    return GeminiEmbeddings(
        configuracion,
        max_reintentos_429=max_reintentos_429,
        espera_maxima=espera_maxima,
    )
