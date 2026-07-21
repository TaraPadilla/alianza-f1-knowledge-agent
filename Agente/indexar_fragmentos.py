"""Reconstruye un índice Chroma sin realizar búsquedas ni recuperación."""

from __future__ import annotations

import argparse

from app.configuracion import ErrorConfiguracion, cargar_configuracion
from app.procesamiento import (
    descubrir_documentos,
    extraer_documentos_markdown,
    fragmentar_documentos,
    reconstruir_indice,
)
from app.procesamiento.embeddings import (
    ErrorConfiguracionEmbeddings,
    cargar_configuracion_embeddings,
    crear_proveedor_embeddings,
)
from app.procesamiento.extractor_markdown import ErrorExtraccionMarkdown
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
    argumentos = parser.parse_args()

    visibilidades = ["Public"] if argumentos.perfil == "public" else ["Public", "Private"]

    try:
        configuracion_proyecto = cargar_configuracion(
            empresa=argumentos.empresa,
            visibilidades=visibilidades,
        )
        descubiertos = descubrir_documentos(configuracion_proyecto)
        extraidos = extraer_documentos_markdown(descubiertos)
        fragmentos = fragmentar_documentos(
            extraidos,
            tamano_maximo=argumentos.tamano_maximo,
            solapamiento=argumentos.solapamiento,
        )
        configuracion = cargar_configuracion_embeddings()
        proveedor = crear_proveedor_embeddings(configuracion)
        resultado = reconstruir_indice(
            fragmentos,
            perfil=argumentos.perfil,
            configuracion=configuracion,
            proveedor=proveedor,
            empresa=configuracion_proyecto.empresa,
        )
    except (
        ErrorConfiguracion,
        ErrorConfiguracionEmbeddings,
        ErrorExtraccionMarkdown,
        ErrorFragmentacion,
        ErrorIndiceVectorial,
    ) as error:
        parser.error(str(error))

    print(
        f"Índice '{resultado.perfil}' reconstruido: "
        f"{resultado.cantidad_fragmentos} fragmentos."
    )
    print(f"Colección: {resultado.coleccion}")
    print(f"Directorio: {resultado.directorio}")


if __name__ == "__main__":
    main()
