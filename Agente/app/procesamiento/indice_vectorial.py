"""Creación y reconstrucción de índices Chroma persistentes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .embeddings import ConfiguracionEmbeddings, ProveedorEmbeddings
from .modelos import FragmentoMarkdown


PerfilIndice = Literal["public", "internal"]
PERFILES_VALIDOS = ("public", "internal")


class ErrorIndiceVectorial(ValueError):
    """Indica que los fragmentos no corresponden al índice solicitado."""


@dataclass(frozen=True)
class ResultadoIndexacion:
    """Resumen seguro de una reconstrucción del índice."""

    perfil: PerfilIndice
    empresa: str
    coleccion: str
    directorio: Path
    cantidad_fragmentos: int


def _nombre_coleccion(empresa: str, perfil: PerfilIndice) -> str:
    """Genera un nombre aceptado por Chroma a partir de empresa y perfil."""

    empresa_normalizada = re.sub(r"[^a-z0-9]+", "_", empresa.casefold()).strip("_")
    if not empresa_normalizada:
        raise ErrorIndiceVectorial("No fue posible generar el nombre de la colección.")
    return f"{empresa_normalizada}_{perfil}"


def _validar_fragmentos(
    fragmentos: list[FragmentoMarkdown],
    perfil: PerfilIndice,
    empresa_solicitada: str | None,
) -> str:
    """Evita mezclar empresas y bloquea Private en el índice público."""

    if perfil not in PERFILES_VALIDOS:
        raise ErrorIndiceVectorial(
            "El perfil debe ser 'public' o 'internal'."
        )
    if not fragmentos:
        if not empresa_solicitada:
            raise ErrorIndiceVectorial(
                "Debe indicarse la empresa para crear un índice vacío."
            )
        return empresa_solicitada

    empresas = {fragmento.empresa for fragmento in fragmentos}
    if len(empresas) != 1:
        raise ErrorIndiceVectorial("Cada índice debe pertenecer a una sola empresa.")
    empresa_fragmentos = next(iter(empresas))
    if empresa_solicitada and empresa_solicitada != empresa_fragmentos:
        raise ErrorIndiceVectorial(
            "La empresa indicada no coincide con los fragmentos."
        )

    visibilidades = {fragmento.visibilidad for fragmento in fragmentos}
    desconocidas = visibilidades.difference({"Public", "Private"})
    if desconocidas:
        raise ErrorIndiceVectorial(
            "Se encontraron visibilidades desconocidas: "
            + ", ".join(sorted(desconocidas))
            + "."
        )
    if perfil == "public" and "Private" in visibilidades:
        raise ErrorIndiceVectorial(
            "El índice public no puede contener fragmentos Private."
        )

    referencias = [fragmento.referencia_fragmento for fragmento in fragmentos]
    if len(referencias) != len(set(referencias)):
        raise ErrorIndiceVectorial(
            "Existen referencias de fragmento duplicadas."
        )

    return empresa_fragmentos


def _metadatos_chroma(
    fragmento: FragmentoMarkdown,
) -> dict[str, str | int]:
    """Convierte todos los metadatos a valores escalares aceptados por Chroma."""

    return {
        clave: "" if valor is None else valor
        for clave, valor in fragmento.metadatos().items()
    }


def _abrir_cliente(directorio: Path):
    """Abre Chroma directamente para evitar dependencias de recuperación."""

    try:
        import chromadb
    except ImportError as error:
        raise ErrorIndiceVectorial(
            "Instala las dependencias de Agente/requirements.txt."
        ) from error
    return chromadb.PersistentClient(path=str(directorio))


def reconstruir_indice(
    fragmentos: list[FragmentoMarkdown],
    perfil: PerfilIndice,
    configuracion: ConfiguracionEmbeddings,
    proveedor: ProveedorEmbeddings,
    *,
    empresa: str | None = None,
) -> ResultadoIndexacion:
    """Recrea por completo un índice para evitar registros duplicados."""

    empresa_validada = _validar_fragmentos(fragmentos, perfil, empresa)
    coleccion = _nombre_coleccion(empresa_validada, perfil)
    directorio = configuracion.directorio_vectorial / empresa_validada / perfil
    directorio.mkdir(parents=True, exist_ok=True)

    cliente = _abrir_cliente(directorio)
    try:
        existentes = {
            coleccion_existente.name
            for coleccion_existente in cliente.list_collections()
        }
        if coleccion in existentes:
            cliente.delete_collection(coleccion)
        almacen = cliente.get_or_create_collection(
            name=coleccion,
            configuration={"hnsw": {"space": "cosine"}},
        )

        if fragmentos:
            documentos = [fragmento.contenido_markdown for fragmento in fragmentos]
            vectores = proveedor.embed_documents(documentos)
            if len(vectores) != len(fragmentos):
                raise ErrorIndiceVectorial(
                    "El proveedor no devolvió un vector por cada fragmento."
                )
            almacen.add(
                ids=[fragmento.referencia_fragmento for fragmento in fragmentos],
                documents=documentos,
                embeddings=vectores,
                metadatas=[_metadatos_chroma(fragmento) for fragmento in fragmentos],
            )
    finally:
        # Chroma mantiene archivos abiertos en Windows hasta cerrar el cliente.
        cliente.close()

    return ResultadoIndexacion(
        perfil=perfil,
        empresa=empresa_validada,
        coleccion=coleccion,
        directorio=directorio,
        cantidad_fragmentos=len(fragmentos),
    )
