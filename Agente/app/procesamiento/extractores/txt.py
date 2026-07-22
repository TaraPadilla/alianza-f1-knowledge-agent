"""Extractor de texto UTF-8 sin estructura adicional."""

from __future__ import annotations

from ..modelos import DocumentoDescubierto, DocumentoExtraido, SeccionMarkdown
from . import ErrorExtraccionDocumento
from .markdown import normalizar_markdown


def extraer_txt(documento: DocumentoDescubierto) -> DocumentoExtraido:
    """Convierte un TXT en una sección del modelo Markdown interno."""

    try:
        contenido = documento.ruta_archivo.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        raise ErrorExtraccionDocumento(
            f"No fue posible leer '{documento.ruta_relativa}' como UTF-8: {error}"
        ) from error

    contenido = normalizar_markdown(contenido)
    secciones = (
        (SeccionMarkdown(None, 0, contenido),)
        if contenido
        else ()
    )
    return DocumentoExtraido(
        empresa=documento.empresa,
        visibilidad=documento.visibilidad,
        ruta_relativa=documento.ruta_relativa,
        secciones=secciones,
        tipo_archivo="txt",
        archivo_original=documento.ruta_archivo.name,
    )
