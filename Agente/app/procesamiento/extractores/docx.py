"""Extractor DOCX que conserva estructura mediante Markdown interno."""

from __future__ import annotations

import re

from ..modelos import DocumentoDescubierto, DocumentoExtraido
from . import ErrorExtraccionDocumento
from .markdown import normalizar_markdown, separar_por_encabezados


PATRON_NIVEL_ENCABEZADO = re.compile(
    r"(?:heading|t[ií]tulo|title)[ _-]?(\d+)$",
    re.IGNORECASE,
)


def _nivel_encabezado(parrafo) -> int | None:
    estilo = parrafo.style
    candidatos = (getattr(estilo, "style_id", ""), getattr(estilo, "name", ""))
    for candidato in candidatos:
        coincidencia = PATRON_NIVEL_ENCABEZADO.search(candidato or "")
        if coincidencia:
            return min(6, max(1, int(coincidencia.group(1))))
    return None


def _es_lista(parrafo) -> bool:
    propiedades = parrafo._p.pPr  # python-docx expone aquí la numeración real.
    tiene_numeracion = propiedades is not None and propiedades.numPr is not None
    estilo = f"{parrafo.style.style_id} {parrafo.style.name}".casefold()
    return tiene_numeracion or "list" in estilo or "lista" in estilo


def _parrafo_a_markdown(parrafo) -> str:
    texto = parrafo.text.strip()
    if not texto:
        return ""
    nivel = _nivel_encabezado(parrafo)
    if nivel:
        return f"{'#' * nivel} {texto}"
    if _es_lista(parrafo):
        estilo = f"{parrafo.style.style_id} {parrafo.style.name}".casefold()
        marcador = "1." if "number" in estilo or "número" in estilo else "-"
        return f"{marcador} {texto}"
    return texto


def _celda_a_markdown(texto: str) -> str:
    return texto.strip().replace("|", "\\|").replace("\n", "<br>")


def _tabla_a_markdown(tabla) -> str:
    filas = [
        [_celda_a_markdown(celda.text) for celda in fila.cells]
        for fila in tabla.rows
    ]
    if not filas:
        return ""
    columnas = max(len(fila) for fila in filas)
    filas = [fila + [""] * (columnas - len(fila)) for fila in filas]
    encabezado = f"| {' | '.join(filas[0])} |"
    separador = f"| {' | '.join(['---'] * columnas)} |"
    cuerpo = [f"| {' | '.join(fila)} |" for fila in filas[1:]]
    return "\n".join((encabezado, separador, *cuerpo))


def extraer_docx(documento: DocumentoDescubierto) -> DocumentoExtraido:
    """Extrae bloques DOCX en orden y los normaliza a Markdown."""

    try:
        from docx import Document
        from docx.table import Table
    except ImportError as error:
        raise ErrorExtraccionDocumento(
            "Falta python-docx. Instala Agente/requirements.txt."
        ) from error

    try:
        archivo_docx = Document(documento.ruta_archivo)
        bloques: list[str] = []
        for bloque in archivo_docx.iter_inner_content():
            convertido = (
                _tabla_a_markdown(bloque)
                if isinstance(bloque, Table)
                else _parrafo_a_markdown(bloque)
            )
            if convertido:
                bloques.append(convertido)
    except Exception as error:
        raise ErrorExtraccionDocumento(
            f"El archivo '{documento.ruta_relativa}' no es un DOCX válido: {error}"
        ) from error

    contenido = normalizar_markdown("\n\n".join(bloques))
    return DocumentoExtraido(
        empresa=documento.empresa,
        visibilidad=documento.visibilidad,
        ruta_relativa=documento.ruta_relativa,
        secciones=separar_por_encabezados(contenido),
        tipo_archivo="docx",
        archivo_original=documento.ruta_archivo.name,
    )
