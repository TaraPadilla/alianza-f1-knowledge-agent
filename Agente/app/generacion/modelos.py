"""Modelos de la salida del LLM y de la respuesta validada."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SalidaLLM:
    """Respuesta estructurada solicitada al modelo de lenguaje."""

    respuesta: str
    informacion_encontrada: bool
    fuentes_utilizadas: tuple[int, ...]

    @classmethod
    def desde_datos(cls, datos: dict) -> "SalidaLLM":
        """Valida los tipos recibidos antes de usarlos en la aplicación."""

        respuesta = datos.get("respuesta")
        encontrada = datos.get("informacion_encontrada")
        fuentes = datos.get("fuentes_utilizadas")
        if not isinstance(respuesta, str):
            raise ValueError("La respuesta estructurada no contiene texto válido.")
        if not isinstance(encontrada, bool):
            raise ValueError(
                "La respuesta estructurada no indica si encontró información."
            )
        if not isinstance(fuentes, list) or any(
            not isinstance(numero, int) or isinstance(numero, bool)
            for numero in fuentes
        ):
            raise ValueError(
                "La respuesta estructurada contiene fuentes inválidas."
            )
        return cls(
            respuesta=respuesta.strip(),
            informacion_encontrada=encontrada,
            fuentes_utilizadas=tuple(fuentes),
        )


@dataclass(frozen=True)
class FuenteRespuesta:
    """Referencia validada que se puede mostrar al colaborador."""

    archivo: str
    seccion: str
    referencia_fragmento: str
    visibilidad: str
    tipo_archivo: str = "markdown"
    pagina: int | None = None


@dataclass(frozen=True)
class RespuestaGenerada:
    """Resultado final con texto y fuentes construidas por Python."""

    texto: str
    informacion_encontrada: bool
    fuentes: tuple[FuenteRespuesta, ...]
