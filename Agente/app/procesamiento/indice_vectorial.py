"""Creación y reconstrucción de índices Chroma persistentes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

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
    nuevos: int
    actualizados: int
    sin_cambios: int
    eliminados: int
    indexacion_completa: bool


ProgresoIndexacion = Callable[[int, int, str, str], None]


def nombre_coleccion(empresa: str, perfil: PerfilIndice) -> str:
    """Genera un nombre aceptado por Chroma a partir de empresa y perfil."""

    if perfil not in PERFILES_VALIDOS:
        raise ErrorIndiceVectorial("El perfil debe ser 'public' o 'internal'.")
    empresa_normalizada = re.sub(r"[^a-z0-9]+", "_", empresa.casefold()).strip("_")
    if not empresa_normalizada:
        raise ErrorIndiceVectorial("No fue posible generar el nombre de la colección.")
    return f"{empresa_normalizada}_{perfil}"


def directorio_indice(
    configuracion: ConfiguracionEmbeddings,
    empresa: str,
    perfil: PerfilIndice,
) -> Path:
    """Devuelve la ubicación portable de un perfil sin crearla."""

    # Validar el perfil aquí evita construir rutas para nombres inesperados.
    nombre_coleccion(empresa, perfil)
    return configuracion.directorio_vectorial / empresa / perfil


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


def _validar_control_ejecucion(
    limite_fragmentos: int | None,
    tamano_lote: int,
) -> None:
    if limite_fragmentos is not None and limite_fragmentos <= 0:
        raise ErrorIndiceVectorial(
            "limite_fragmentos debe ser mayor que cero."
        )
    if tamano_lote <= 0:
        raise ErrorIndiceVectorial("tamano_lote debe ser mayor que cero.")


def _registro_esta_actualizado(
    fragmento: FragmentoMarkdown,
    documento_existente: str | None,
    metadatos_existentes: dict | None,
) -> bool:
    return (
        documento_existente == fragmento.contenido_markdown
        and metadatos_existentes == _metadatos_chroma(fragmento)
    )


def reconstruir_indice(
    fragmentos: list[FragmentoMarkdown],
    perfil: PerfilIndice,
    configuracion: ConfiguracionEmbeddings,
    proveedor: ProveedorEmbeddings,
    *,
    empresa: str | None = None,
    limite_fragmentos: int | None = None,
    tamano_lote: int = 25,
    progreso: ProgresoIndexacion | None = None,
) -> ResultadoIndexacion:
    """Actualiza un índice por lotes y permite reanudar tras un fallo.

    Los registros existentes no se eliminan al comenzar. Los obsoletos solo se
    borran después de terminar correctamente una indexación sin límite.
    """

    _validar_control_ejecucion(limite_fragmentos, tamano_lote)
    empresa_validada = _validar_fragmentos(fragmentos, perfil, empresa)
    coleccion = nombre_coleccion(empresa_validada, perfil)
    directorio = directorio_indice(configuracion, empresa_validada, perfil)
    directorio.mkdir(parents=True, exist_ok=True)
    seleccionados = (
        fragmentos[:limite_fragmentos]
        if limite_fragmentos is not None
        else fragmentos
    )
    indexacion_completa = limite_fragmentos is None

    cliente = _abrir_cliente(directorio)
    try:
        almacen = cliente.get_or_create_collection(
            name=coleccion,
            configuration={"hnsw": {"space": "cosine"}},
        )

        datos_existentes = almacen.get(include=["documents", "metadatas"])
        ids_existentes = datos_existentes["ids"]
        documentos_existentes = datos_existentes["documents"] or []
        metadatos_existentes = datos_existentes["metadatas"] or []
        por_id = {
            identificador: (documento, metadatos)
            for identificador, documento, metadatos in zip(
                ids_existentes,
                documentos_existentes,
                metadatos_existentes,
                strict=True,
            )
        }

        pendientes: list[FragmentoMarkdown] = []
        nuevos = 0
        actualizados = 0
        sin_cambios = 0

        for fragmento in seleccionados:
            existente = por_id.get(fragmento.referencia_fragmento)
            if existente is None:
                nuevos += 1
                pendientes.append(fragmento)
            elif _registro_esta_actualizado(fragmento, *existente):
                sin_cambios += 1
            else:
                actualizados += 1
                pendientes.append(fragmento)

        procesados = 0
        total_pendientes = len(pendientes)
        for inicio in range(0, total_pendientes, tamano_lote):
            lote = pendientes[inicio : inicio + tamano_lote]
            documentos = [fragmento.contenido_markdown for fragmento in lote]
            vectores = proveedor.embed_documents(documentos)
            if len(vectores) != len(lote):
                raise ErrorIndiceVectorial(
                    "El proveedor no devolvió un vector por cada fragmento."
                )
            almacen.upsert(
                ids=[fragmento.referencia_fragmento for fragmento in lote],
                documents=documentos,
                embeddings=vectores,
                metadatas=[_metadatos_chroma(fragmento) for fragmento in lote],
            )

            for fragmento in lote:
                procesados += 1
                if progreso:
                    estado = (
                        "actualizado"
                        if fragmento.referencia_fragmento in por_id
                        else "guardado"
                    )
                    progreso(
                        procesados,
                        total_pendientes,
                        estado,
                        fragmento.referencia_fragmento,
                    )

        eliminados = 0
        if indexacion_completa:
            ids_actuales = {
                fragmento.referencia_fragmento for fragmento in fragmentos
            }
            ids_obsoletos = sorted(set(ids_existentes).difference(ids_actuales))
            if ids_obsoletos:
                almacen.delete(ids=ids_obsoletos)
                eliminados = len(ids_obsoletos)
    finally:
        # Chroma mantiene archivos abiertos en Windows hasta cerrar el cliente.
        cliente.close()

    return ResultadoIndexacion(
        perfil=perfil,
        empresa=empresa_validada,
        coleccion=coleccion,
        directorio=directorio,
        cantidad_fragmentos=len(seleccionados),
        nuevos=nuevos,
        actualizados=actualizados,
        sin_cambios=sin_cambios,
        eliminados=eliminados,
        indexacion_completa=indexacion_completa,
    )
