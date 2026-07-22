"""Reconstruye un índice Chroma sin realizar búsquedas ni recuperación."""

from __future__ import annotations

import argparse

from app.configuracion import ErrorConfiguracion, cargar_configuracion
from app.procesamiento import (
    ErrorExtraccionDocumento,
    descubrir_documentos,
    extraer_documentos,
    fragmentar_documentos,
    reconstruir_indice,
)
from app.procesamiento.embeddings import (
    ErrorEmbeddings,
    ErrorConfiguracionEmbeddings,
    cargar_configuracion_embeddings,
    crear_proveedor_embeddings,
)
from app.procesamiento.fragmentacion import ErrorFragmentacion
from app.procesamiento.indice_vectorial import ErrorIndiceVectorial


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera embeddings y reconstruye un índice local.",
    )
    parser.add_argument("perfil", choices=("public", "internal"))
    parser.add_argument("--empresa", help="Usa EMPRESA_ACTIVA si se omite.")
    parser.add_argument("--tamano-maximo", type=int, default=1000)
    parser.add_argument("--solapamiento", type=int, default=150)
    parser.add_argument(
        "--limite-fragmentos",
        type=int,
        help="Procesa solo los primeros N fragmentos sin eliminar obsoletos.",
    )
    parser.add_argument("--tamano-lote", type=int, default=25)
    parser.add_argument("--espera-maxima", type=float, default=45.0)
    argumentos = parser.parse_args()

    visibilidades = ["Public"] if argumentos.perfil == "public" else ["Public", "Private"]

    try:
        configuracion_proyecto = cargar_configuracion(
            empresa=argumentos.empresa,
            visibilidades=visibilidades,
        )
        descubiertos = descubrir_documentos(configuracion_proyecto)
        extraidos = extraer_documentos(descubiertos)
        fragmentos = fragmentar_documentos(
            extraidos,
            tamano_maximo=argumentos.tamano_maximo,
            solapamiento=argumentos.solapamiento,
        )
        configuracion = cargar_configuracion_embeddings()
        proveedor = crear_proveedor_embeddings(
            configuracion,
            max_reintentos_429=2,
            espera_maxima=argumentos.espera_maxima,
        )

        def mostrar_progreso(
            actual: int,
            total: int,
            estado: str,
            referencia: str,
        ) -> None:
            print(f"Fragmento {actual}/{total}: {estado} | {referencia}")

        resultado = reconstruir_indice(
            fragmentos,
            perfil=argumentos.perfil,
            configuracion=configuracion,
            proveedor=proveedor,
            empresa=configuracion_proyecto.empresa,
            limite_fragmentos=argumentos.limite_fragmentos,
            tamano_lote=argumentos.tamano_lote,
            progreso=mostrar_progreso,
        )
    except (
        ErrorConfiguracion,
        ErrorConfiguracionEmbeddings,
        ErrorEmbeddings,
        ErrorExtraccionDocumento,
        ErrorFragmentacion,
        ErrorIndiceVectorial,
    ) as error:
        parser.error(str(error))

    print(
        f"Índice '{resultado.perfil}' actualizado: "
        f"{resultado.cantidad_fragmentos} fragmentos."
    )
    print(
        f"Nuevos: {resultado.nuevos} | "
        f"actualizados: {resultado.actualizados} | "
        f"sin cambios: {resultado.sin_cambios} | "
        f"eliminados: {resultado.eliminados}"
    )
    if not resultado.indexacion_completa:
        print("Ejecución parcial: no se eliminaron registros existentes.")
    print(f"Colección: {resultado.coleccion}")
    print(f"Directorio: {resultado.directorio}")


if __name__ == "__main__":
    main()
