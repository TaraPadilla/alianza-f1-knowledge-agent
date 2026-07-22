"""Extractores registrados para convertir documentos a Markdown interno."""


class ErrorExtraccionDocumento(ValueError):
    """Indica que un documento no pudo convertirse al modelo interno."""


from .selector import (  # noqa: E402: el error debe existir antes del registro.
    EXTENSIONES_CARGADOR,
    EXTENSIONES_REGISTRADAS,
    EXTENSIONES_SOPORTADAS,
    extraer_documento,
    extraer_documentos,
    obtener_extractor,
    validar_extension,
)

__all__ = [
    "EXTENSIONES_CARGADOR",
    "EXTENSIONES_REGISTRADAS",
    "EXTENSIONES_SOPORTADAS",
    "ErrorExtraccionDocumento",
    "extraer_documento",
    "extraer_documentos",
    "obtener_extractor",
    "validar_extension",
]
