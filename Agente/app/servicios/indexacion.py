"""Actualización de índices reutilizable por la interfaz local."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..configuracion import cargar_configuracion
from ..procesamiento import (
    descubrir_documentos,
    extraer_documentos,
    fragmentar_documentos,
    reconstruir_indice,
)
from ..procesamiento.embeddings import (
    cargar_configuracion_embeddings,
    crear_proveedor_embeddings,
)
from ..procesamiento.indice_vectorial import (
    EstadoIndice,
    PerfilIndice,
    ResultadoIndexacion,
    consultar_estado_indice,
)


ProgresoInterfaz = Callable[[PerfilIndice, int, int, str, str], None]


def actualizar_conocimiento(
    empresa: str,
    visibilidad_modificada: str,
    *,
    tamano_maximo: int = 1000,
    solapamiento: int = 150,
    tamano_lote: int = 25,
    espera_maxima: float = 45.0,
    progreso: ProgresoInterfaz | None = None,
) -> tuple[ResultadoIndexacion, ...]:
    """Actualiza los perfiles afectados por cambios en Public o Private."""

    if visibilidad_modificada not in {"Public", "Private"}:
        raise ValueError("La visibilidad debe ser Public o Private.")
    perfiles: tuple[PerfilIndice, ...] = (
        ("public", "internal")
        if visibilidad_modificada == "Public"
        else ("internal",)
    )
    configuracion_embeddings = cargar_configuracion_embeddings()
    proveedor = crear_proveedor_embeddings(
        configuracion_embeddings,
        max_reintentos_429=2,
        espera_maxima=espera_maxima,
    )
    resultados: list[ResultadoIndexacion] = []

    for perfil in perfiles:
        visibilidades = (
            ("Public",) if perfil == "public" else ("Public", "Private")
        )
        configuracion_proyecto = cargar_configuracion(
            empresa=empresa,
            visibilidades=visibilidades,
        )
        fragmentos = fragmentar_documentos(
            extraer_documentos(
                descubrir_documentos(configuracion_proyecto)
            ),
            tamano_maximo=tamano_maximo,
            solapamiento=solapamiento,
        )
        resultados.append(
            reconstruir_indice(
                fragmentos,
                perfil,
                configuracion_embeddings,
                proveedor,
                empresa=empresa,
                tamano_lote=tamano_lote,
                progreso=(
                    (
                        lambda actual, total, estado, referencia, perfil=perfil: progreso(
                            perfil,
                            actual,
                            total,
                            estado,
                            referencia,
                        )
                    )
                    if progreso
                    else None
                ),
            )
        )
    return tuple(resultados)


def obtener_estado_indexacion(
    empresa: str,
    perfil: PerfilIndice,
    *,
    visibilidad: str | None = None,
) -> EstadoIndice:
    """Obtiene las métricas persistidas de una colección vectorial."""

    configuracion_embeddings = cargar_configuracion_embeddings()
    return consultar_estado_indice(
        configuracion_embeddings,
        empresa,
        perfil,
        visibilidad=visibilidad,
    )


def obtener_cantidad_fragmentos(
    empresa: str,
    perfil: PerfilIndice,
    *,
    visibilidad: str | None = None,
) -> int:
    """Mantiene una consulta simple para otros consumidores del servicio."""

    return obtener_estado_indexacion(
        empresa,
        perfil,
        visibilidad=visibilidad,
    ).cantidad_fragmentos


def obtener_fecha_ultima_indexacion(
    empresa: str,
    perfil: PerfilIndice,
) -> datetime | None:
    """Devuelve la fecha de la última indexación completa y exitosa."""

    return obtener_estado_indexacion(empresa, perfil).ultima_indexacion
