"""Listado y carga local de documentos admitidos por el pipeline actual."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable, Protocol

from ..configuracion import RAIZ_AGENTE, Configuracion, cargar_configuracion
from ..procesamiento import (
    EXTENSIONES_CARGADOR,
    EXTENSIONES_SOPORTADAS,
    DocumentoDescubierto,
    descubrir_documentos,
    extraer_documento,
)
from ..procesamiento.extractores import validar_extension


class ArchivoCargado(Protocol):
    """Parte de la interfaz de UploadedFile que necesita este servicio."""

    name: str

    def getvalue(self) -> bytes:
        """Devuelve el contenido binario recibido por la interfaz."""


@dataclass(frozen=True)
class DocumentoInterfaz:
    nombre: str
    ruta_relativa: str
    visibilidad: str
    tamano_bytes: int


def listar_empresas(raiz_agente: Path | None = None) -> tuple[str, ...]:
    """Localiza empresas que tengan la estructura Public y Private."""

    raiz = (raiz_agente or RAIZ_AGENTE).resolve()
    empresas = [
        ruta.name
        for ruta in raiz.iterdir()
        if ruta.is_dir()
        and (ruta / "Public").is_dir()
        and (ruta / "Private").is_dir()
    ]
    return tuple(sorted(empresas, key=str.casefold))


def listar_documentos(
    empresa: str,
    visibilidad: str,
    *,
    raiz_agente: Path | None = None,
) -> tuple[DocumentoInterfaz, ...]:
    """Devuelve documentos seguros para mostrar, sin contenido ni rutas absolutas."""

    configuracion = cargar_configuracion(
        empresa=empresa,
        visibilidades=(visibilidad,),
        raiz_agente=raiz_agente,
    )
    resultado: list[DocumentoInterfaz] = []
    for documento in descubrir_documentos(configuracion):
        resultado.append(
            DocumentoInterfaz(
                nombre=documento.ruta_archivo.name,
                ruta_relativa=documento.ruta_relativa,
                visibilidad=documento.visibilidad,
                tamano_bytes=documento.ruta_archivo.stat().st_size,
            )
        )
    return tuple(resultado)


def _validar_nombre_archivo(nombre: str) -> str:
    limpio = nombre.strip()
    if not limpio or Path(limpio).name != limpio:
        raise ValueError("El archivo debe tener un nombre simple y seguro.")
    validar_extension(limpio)
    return limpio


def guardar_documentos(
    archivos: Iterable[ArchivoCargado],
    empresa: str,
    visibilidad: str,
    *,
    raiz_agente: Path | None = None,
) -> tuple[str, ...]:
    """Guarda archivos validados dentro del nivel seleccionado."""

    configuracion: Configuracion = cargar_configuracion(
        empresa=empresa,
        visibilidades=(visibilidad,),
        raiz_agente=raiz_agente,
    )
    destino = configuracion.ruta_empresa / visibilidad
    guardados: list[str] = []
    for archivo in archivos:
        nombre = _validar_nombre_archivo(archivo.name)
        contenido = archivo.getvalue()
        ruta_temporal: Path | None = None
        try:
            # La misma extracción del pipeline valida la carga antes de reemplazar
            # un archivo existente. Así no se duplica lógica por formato.
            with NamedTemporaryFile(
                prefix=".carga-",
                suffix=Path(nombre).suffix,
                dir=destino,
                delete=False,
            ) as temporal:
                temporal.write(contenido)
                ruta_temporal = Path(temporal.name)

            extraer_documento(
                DocumentoDescubierto(
                    empresa=configuracion.empresa,
                    visibilidad=visibilidad,
                    ruta_relativa=(
                        f"{configuracion.empresa}/{visibilidad}/{nombre}"
                    ),
                    ruta_archivo=ruta_temporal,
                )
            )
            ruta_temporal.replace(destino / nombre)
            ruta_temporal = None
        finally:
            if ruta_temporal is not None and ruta_temporal.exists():
                ruta_temporal.unlink()
        guardados.append(nombre)
    return tuple(guardados)
