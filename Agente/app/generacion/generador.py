"""Genera y valida una respuesta a partir de fragmentos ya recuperados."""

from __future__ import annotations

from pathlib import PurePosixPath

from ..recuperacion.contexto import ensamblar_contexto
from ..recuperacion.modelos import FragmentoRecuperado
from .modelos import FuenteRespuesta, RespuestaGenerada
from .prompts import INSTRUCCION_SISTEMA, crear_mensaje_usuario
from .proveedor_llm import ProveedorLLM


FALLBACK_SIN_INFORMACION = (
    "No encontré esta información en los documentos disponibles."
)


class ErrorGeneracion(ValueError):
    """Indica que no se proporcionó una pregunta válida."""


def _respuesta_fallback() -> RespuestaGenerada:
    return RespuestaGenerada(
        texto=FALLBACK_SIN_INFORMACION,
        informacion_encontrada=False,
        fuentes=(),
    )


def _fuente(fragmento: FragmentoRecuperado) -> FuenteRespuesta:
    ruta_portable = fragmento.ruta_relativa.replace("\\", "/")
    return FuenteRespuesta(
        archivo=(
            fragmento.archivo_original or PurePosixPath(ruta_portable).name
        ),
        seccion=fragmento.titulo_seccion or "Sin encabezado",
        referencia_fragmento=fragmento.referencia_fragmento,
        visibilidad=fragmento.visibilidad,
        tipo_archivo=fragmento.tipo_archivo,
        pagina=fragmento.pagina,
    )


def _formatear_respuesta(texto: str, fuentes: tuple[FuenteRespuesta, ...]) -> str:
    referencias = "\n".join(
        f"- {fuente.archivo} — "
        + (
            f"Página: {fuente.pagina} "
            if fuente.pagina is not None
            else f"Sección: {fuente.seccion} "
        )
        + f"— Referencia: {fuente.referencia_fragmento}"
        for fuente in fuentes
    )
    return f"{texto.strip()}\n\nFuentes:\n{referencias}"


def generar_respuesta(
    pregunta: str,
    fragmentos: list[FragmentoRecuperado],
    proveedor: ProveedorLLM,
) -> RespuestaGenerada:
    """Genera una respuesta y rechaza citas que no existan en el contexto."""

    pregunta_limpia = pregunta.strip()
    if not pregunta_limpia:
        raise ErrorGeneracion("La pregunta no puede estar vacía.")
    if not fragmentos:
        # No se consume el LLM cuando la recuperación no encontró contexto.
        return _respuesta_fallback()

    contexto = ensamblar_contexto(fragmentos)
    salida = proveedor.generar(
        INSTRUCCION_SISTEMA,
        crear_mensaje_usuario(pregunta_limpia, contexto),
    )
    if (
        not salida.informacion_encontrada
        or not salida.respuesta
        or not salida.fuentes_utilizadas
    ):
        return _respuesta_fallback()

    numeros_validos = range(1, len(fragmentos) + 1)
    if any(numero not in numeros_validos for numero in salida.fuentes_utilizadas):
        return _respuesta_fallback()

    # Conservar el primer uso de cada fuente evita citas duplicadas.
    numeros_unicos = tuple(dict.fromkeys(salida.fuentes_utilizadas))
    fuentes = tuple(_fuente(fragmentos[numero - 1]) for numero in numeros_unicos)
    return RespuestaGenerada(
        texto=_formatear_respuesta(salida.respuesta, fuentes),
        informacion_encontrada=True,
        fuentes=fuentes,
    )
