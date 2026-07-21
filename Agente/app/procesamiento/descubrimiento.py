"""Localiza documentos Markdown sin extraer su contenido."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..configuracion import Configuracion, cargar_configuracion
from .modelos import DocumentoDescubierto


EXTENSIONES_MARKDOWN = {".md", ".markdown"}


def _es_ruta_oculta(ruta: Path) -> bool:
    """Indica si alguna parte de la ruta comienza por punto."""

    return any(parte.startswith(".") for parte in ruta.parts)


def descubrir_documentos(
    configuracion: Configuracion,
) -> list[DocumentoDescubierto]:
    """Descubre Markdown en las visibilidades habilitadas de una empresa.

    Esta función solo inspecciona nombres y rutas. La lectura del contenido se
    realizará posteriormente en el extractor Markdown.
    """

    documentos: list[DocumentoDescubierto] = []

    for visibilidad, ruta_nivel in zip(
        configuracion.visibilidades,
        configuracion.rutas_conocimiento,
        strict=True,
    ):
        for ruta_archivo in ruta_nivel.rglob("*"):
            ruta_dentro_del_nivel = ruta_archivo.relative_to(ruta_nivel)

            if _es_ruta_oculta(ruta_dentro_del_nivel):
                continue
            if ruta_archivo.is_symlink() or not ruta_archivo.is_file():
                continue
            if ruta_archivo.suffix.lower() not in EXTENSIONES_MARKDOWN:
                continue

            # Se almacena una ruta con separadores "/" para que el metadato sea
            # igual en Windows, Linux y el futuro despliegue en OCI.
            ruta_relativa = ruta_archivo.relative_to(
                configuracion.raiz_agente
            ).as_posix()

            documentos.append(
                DocumentoDescubierto(
                    empresa=configuracion.empresa,
                    visibilidad=visibilidad,
                    ruta_relativa=ruta_relativa,
                    ruta_archivo=ruta_archivo,
                )
            )

    # Un orden determinista facilita las pruebas y hará reproducible el chunking.
    return sorted(
        documentos,
        key=lambda documento: documento.ruta_relativa.casefold(),
    )


def descubrir_conocimiento(
    empresa: str | None = None,
    visibilidades: str | Iterable[str] | None = None,
    *,
    raiz_agente: Path | None = None,
    ruta_env: Path | None = None,
) -> list[DocumentoDescubierto]:
    """Carga la configuración y descubre los Markdown de la empresa activa."""

    configuracion = cargar_configuracion(
        empresa=empresa,
        visibilidades=visibilidades,
        raiz_agente=raiz_agente,
        ruta_env=ruta_env,
    )
    return descubrir_documentos(configuracion)
