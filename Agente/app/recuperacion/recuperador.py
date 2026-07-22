"""Consulta semántica sobre los índices Chroma ya construidos."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..procesamiento.embeddings import ConfiguracionEmbeddings, ProveedorEmbeddings
from ..procesamiento.indice_vectorial import (
    PERFILES_VALIDOS,
    PerfilIndice,
    directorio_indice,
    nombre_coleccion,
)
from .modelos import FiltrosRecuperacion, FragmentoRecuperado


class ErrorRecuperacion(ValueError):
    """Indica que la consulta o el índice solicitado no son válidos."""


def _validar_consulta(
    pregunta: str,
    perfil: PerfilIndice,
    empresa: str,
    top_k: int,
    filtros: FiltrosRecuperacion,
) -> str:
    texto = pregunta.strip()
    if not texto:
        raise ErrorRecuperacion("La pregunta no puede estar vacía.")
    if perfil not in PERFILES_VALIDOS:
        raise ErrorRecuperacion("El perfil debe ser 'public' o 'internal'.")
    empresa_limpia = empresa.strip()
    if not empresa_limpia:
        raise ErrorRecuperacion("Debe indicarse la empresa que se consultará.")
    if empresa_limpia in {".", ".."} or Path(empresa_limpia).name != empresa_limpia:
        raise ErrorRecuperacion(
            "La empresa debe ser un nombre de carpeta, no una ruta."
        )
    if top_k <= 0:
        raise ErrorRecuperacion("top_k debe ser mayor que cero.")
    if filtros.visibilidad not in {None, "Public", "Private"}:
        raise ErrorRecuperacion(
            "La visibilidad del filtro debe ser 'Public' o 'Private'."
        )
    if perfil == "public" and filtros.visibilidad == "Private":
        raise ErrorRecuperacion(
            "El perfil public no permite consultar visibilidad Private."
        )
    return texto


def _crear_filtro_chroma(filtros: FiltrosRecuperacion) -> dict | None:
    condiciones: list[dict[str, Any]] = []
    if filtros.visibilidad:
        condiciones.append({"visibilidad": filtros.visibilidad})
    if filtros.ruta_relativa:
        condiciones.append({"ruta_relativa": filtros.ruta_relativa})
    if filtros.titulo_seccion is not None:
        # Durante la indexación, un título ausente se guarda como cadena vacía.
        condiciones.append({"titulo_seccion": filtros.titulo_seccion})

    if not condiciones:
        return None
    if len(condiciones) == 1:
        return condiciones[0]
    return {"$and": condiciones}


def recuperar_fragmentos(
    pregunta: str,
    perfil: PerfilIndice,
    configuracion: ConfiguracionEmbeddings,
    proveedor: ProveedorEmbeddings,
    *,
    empresa: str,
    top_k: int = 5,
    filtros: FiltrosRecuperacion | None = None,
) -> list[FragmentoRecuperado]:
    """Recupera los fragmentos más cercanos sin crear ni modificar el índice."""

    filtros_aplicados = filtros or FiltrosRecuperacion()
    texto = _validar_consulta(
        pregunta,
        perfil,
        empresa,
        top_k,
        filtros_aplicados,
    )
    directorio = directorio_indice(configuracion, empresa, perfil)
    if not directorio.is_dir():
        raise ErrorRecuperacion(
            f"No existe el índice {perfil} de la empresa '{empresa}'."
        )

    try:
        import chromadb
    except ImportError as error:
        raise ErrorRecuperacion(
            "Instala las dependencias de Agente/requirements.txt."
        ) from error

    cliente = chromadb.PersistentClient(path=str(directorio))
    try:
        nombre = nombre_coleccion(empresa, perfil)
        disponibles = {coleccion.name for coleccion in cliente.list_collections()}
        if nombre not in disponibles:
            raise ErrorRecuperacion(
                f"No existe la colección '{nombre}'. Ejecuta primero la indexación."
            )

        coleccion = cliente.get_collection(nombre)
        if coleccion.count() == 0:
            return []

        vector = proveedor.embed_query(texto)
        if not vector:
            raise ErrorRecuperacion(
                "El proveedor devolvió un embedding vacío para la pregunta."
            )

        parametros: dict[str, Any] = {
            "query_embeddings": [vector],
            "n_results": min(top_k, coleccion.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        filtro_chroma = _crear_filtro_chroma(filtros_aplicados)
        if filtro_chroma:
            parametros["where"] = filtro_chroma
        respuesta = coleccion.query(**parametros)
    finally:
        # Liberar los archivos persistentes evita bloqueos en Windows.
        cliente.close()

    documentos = (respuesta.get("documents") or [[]])[0] or []
    metadatos = (respuesta.get("metadatas") or [[]])[0] or []
    distancias = (respuesta.get("distances") or [[]])[0] or []
    if not (len(documentos) == len(metadatos) == len(distancias)):
        raise ErrorRecuperacion("Chroma devolvió un resultado incompleto.")

    return [
        FragmentoRecuperado.desde_chroma(documento, distancia, metadata)
        for documento, distancia, metadata in zip(
            documentos,
            distancias,
            metadatos,
            strict=True,
        )
    ]
