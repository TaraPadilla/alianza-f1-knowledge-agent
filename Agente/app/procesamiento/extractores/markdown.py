"""Lectura de Markdown conservando su estructura y sintaxis."""

from __future__ import annotations

import re

from ..modelos import DocumentoDescubierto, DocumentoExtraido, SeccionMarkdown
from . import ErrorExtraccionDocumento


PATRON_ENCABEZADO = re.compile(
    r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$"
)
PATRON_APERTURA_CODIGO = re.compile(r"^\s*(`{3,}|~{3,})")
PATRON_LINEAS_VACIAS = re.compile(r"\n{3,}")


def normalizar_markdown(contenido: str) -> str:
    """Normaliza saltos técnicos sin alterar tablas, listas ni código."""

    contenido = contenido.replace("\r\n", "\n").replace("\r", "\n")
    lineas = ["" if not linea.strip() else linea for linea in contenido.split("\n")]
    normalizado = "\n".join(lineas).strip("\n")
    return PATRON_LINEAS_VACIAS.sub("\n\n", normalizado)


def _datos_encabezado(linea: str) -> tuple[str, int] | None:
    coincidencia = PATRON_ENCABEZADO.match(linea)
    if not coincidencia:
        return None
    return coincidencia.group(2), len(coincidencia.group(1))


def separar_por_encabezados(contenido: str) -> tuple[SeccionMarkdown, ...]:
    """Separa Markdown sin interpretar encabezados dentro de bloques de código."""

    if not contenido:
        return ()

    secciones: list[SeccionMarkdown] = []
    lineas_actuales: list[str] = []
    titulo_actual: str | None = None
    nivel_actual = 0
    cierre_codigo: tuple[str, int] | None = None

    def guardar_seccion() -> None:
        markdown = "\n".join(lineas_actuales).strip("\n")
        if markdown:
            secciones.append(
                SeccionMarkdown(
                    titulo=titulo_actual,
                    nivel=nivel_actual,
                    contenido_markdown=markdown,
                )
            )

    for linea in contenido.split("\n"):
        apertura_codigo = PATRON_APERTURA_CODIGO.match(linea)

        if cierre_codigo is not None:
            lineas_actuales.append(linea)
            marcador, longitud = cierre_codigo
            if re.match(rf"^\s*{re.escape(marcador)}{{{longitud},}}\s*$", linea):
                cierre_codigo = None
            continue

        if apertura_codigo:
            simbolos = apertura_codigo.group(1)
            cierre_codigo = (simbolos[0], len(simbolos))
            lineas_actuales.append(linea)
            continue

        encabezado = _datos_encabezado(linea)
        if encabezado:
            guardar_seccion()
            lineas_actuales = [linea]
            titulo_actual, nivel_actual = encabezado
            continue

        lineas_actuales.append(linea)

    guardar_seccion()
    return tuple(secciones)


def extraer_markdown(documento: DocumentoDescubierto) -> DocumentoExtraido:
    """Lee UTF-8 y conserva el Markdown original como formato interno."""

    try:
        contenido = documento.ruta_archivo.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        raise ErrorExtraccionDocumento(
            f"No fue posible leer '{documento.ruta_relativa}' como UTF-8: {error}"
        ) from error

    contenido = normalizar_markdown(contenido)
    return DocumentoExtraido(
        empresa=documento.empresa,
        visibilidad=documento.visibilidad,
        ruta_relativa=documento.ruta_relativa,
        secciones=separar_por_encabezados(contenido),
        tipo_archivo="markdown",
        archivo_original=documento.ruta_archivo.name,
    )
