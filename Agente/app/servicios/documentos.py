"""Listado y carga local de documentos admitidos por el pipeline actual."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from ..configuracion import RAIZ_AGENTE, Configuracion, cargar_configuracion
from ..procesamiento import descubrir_documentos


# La interfaz consulta esta constante. Al agregar un extractor nuevo bastará
# con ampliar aquí sus extensiones, sin rediseñar el cargador visual.
FORMATOS_SOPORTADOS = {"Markdown": ("md", "markdown")}
EXTENSIONES_SOPORTADAS = tuple(
    extension
    for extensiones in FORMATOS_SOPORTADOS.values()
    for extension in extensiones
)


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
    extension = Path(limpio).suffix.casefold().lstrip(".")
    if extension not in EXTENSIONES_SOPORTADAS:
        permitidas = ", ".join(f".{valor}" for valor in EXTENSIONES_SOPORTADAS)
        raise ValueError(f"Formato no soportado. Usa: {permitidas}.")
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
        # Validar UTF-8 aquí permite fallar antes de llegar al extractor.
        try:
            contenido.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError(f"'{nombre}' no contiene texto UTF-8 válido.") from error
        (destino / nombre).write_bytes(contenido)
        guardados.append(nombre)
    return tuple(guardados)
