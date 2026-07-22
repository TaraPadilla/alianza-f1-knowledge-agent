"""Extractor para PDF con capa de texto nativa."""

from __future__ import annotations

from ..modelos import DocumentoDescubierto, DocumentoExtraido, SeccionMarkdown
from . import ErrorExtraccionDocumento
from .markdown import normalizar_markdown


MENSAJE_PDF_SIN_TEXTO = (
    "El PDF no contiene texto extraíble. Probablemente es un PDF escaneado "
    "y OCR aún no está soportado."
)


def extraer_pdf(documento: DocumentoDescubierto) -> DocumentoExtraido:
    """Extrae una sección por página y conserva su número en metadatos."""

    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise ErrorExtraccionDocumento(
            "Falta pypdf. Instala Agente/requirements.txt."
        ) from error

    try:
        lector = PdfReader(documento.ruta_archivo)
        if lector.is_encrypted:
            raise ErrorExtraccionDocumento(
                f"El PDF '{documento.ruta_relativa}' está protegido con contraseña."
            )

        secciones: list[SeccionMarkdown] = []
        for numero, pagina in enumerate(lector.pages, start=1):
            texto = normalizar_markdown(pagina.extract_text() or "")
            if not texto:
                continue
            titulo = f"Página {numero}"
            secciones.append(
                SeccionMarkdown(
                    titulo=titulo,
                    nivel=2,
                    contenido_markdown=f"## {titulo}\n\n{texto}",
                    pagina=numero,
                )
            )
    except ErrorExtraccionDocumento:
        raise
    except Exception as error:
        raise ErrorExtraccionDocumento(
            f"No fue posible leer el PDF '{documento.ruta_relativa}': {error}"
        ) from error

    if not secciones:
        raise ErrorExtraccionDocumento(MENSAJE_PDF_SIN_TEXTO)

    return DocumentoExtraido(
        empresa=documento.empresa,
        visibilidad=documento.visibilidad,
        ruta_relativa=documento.ruta_relativa,
        secciones=tuple(secciones),
        tipo_archivo="pdf",
        archivo_original=documento.ruta_archivo.name,
    )
