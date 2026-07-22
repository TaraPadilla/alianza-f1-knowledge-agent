"""Registro único que relaciona extensiones con extractores."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from ..modelos import DocumentoDescubierto, DocumentoExtraido
from . import ErrorExtraccionDocumento
from .docx import extraer_docx
from .markdown import extraer_markdown
from .pdf import extraer_pdf
from .txt import extraer_txt


Extractor = Callable[[DocumentoDescubierto], DocumentoExtraido]

# Para agregar un formato solo se crea su extractor y se registra aquí.
REGISTRO_EXTRACTORES: dict[str, Extractor] = {
    ".md": extraer_markdown,
    ".markdown": extraer_markdown,
    ".txt": extraer_txt,
    ".docx": extraer_docx,
    ".pdf": extraer_pdf,
}
EXTENSIONES_REGISTRADAS = frozenset(REGISTRO_EXTRACTORES)
EXTENSIONES_SOPORTADAS = tuple(
    extension.lstrip(".") for extension in REGISTRO_EXTRACTORES
)
# Se permite seleccionarlo para devolver la orientación solicitada por el reto.
EXTENSIONES_CARGADOR = (*EXTENSIONES_SOPORTADAS, "doc")


def validar_extension(nombre: str | Path) -> str:
    """Valida una extensión y centraliza los mensajes para formatos rechazados."""

    extension = Path(nombre).suffix.casefold()
    if extension == ".doc":
        raise ErrorExtraccionDocumento(
            "El formato .doc no está soportado actualmente. "
            "Convierte el archivo a .docx."
        )
    if extension not in REGISTRO_EXTRACTORES:
        permitidas = ", ".join(f".{valor}" for valor in EXTENSIONES_SOPORTADAS)
        raise ErrorExtraccionDocumento(
            f"Formato no soportado. Usa: {permitidas}."
        )
    return extension


def obtener_extractor(nombre: str | Path) -> Extractor:
    """Devuelve el extractor registrado para un nombre de archivo."""

    return REGISTRO_EXTRACTORES[validar_extension(nombre)]


def extraer_documento(documento: DocumentoDescubierto) -> DocumentoExtraido:
    """Ejecuta el extractor correspondiente sin conocer el formato aguas arriba."""

    return obtener_extractor(documento.ruta_archivo)(documento)


def extraer_documentos(
    documentos: Iterable[DocumentoDescubierto],
) -> list[DocumentoExtraido]:
    """Extrae documentos heterogéneos conservando su orden determinista."""

    return [extraer_documento(documento) for documento in documentos]
