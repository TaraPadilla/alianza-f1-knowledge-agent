"""Inspecciona el chunking sin imprimir contenido empresarial."""

from __future__ import annotations

import argparse

from app.configuracion import ErrorConfiguracion
from app.procesamiento import (
    descubrir_conocimiento,
    extraer_documentos_markdown,
    fragmentar_documento,
)
from app.procesamiento.extractor_markdown import ErrorExtraccionMarkdown
from app.procesamiento.fragmentacion import ErrorFragmentacion


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resume la fragmentación Markdown sin mostrar su contenido.",
    )
    parser.add_argument(
        "--empresa",
        help="Nombre de la empresa. Si se omite, se usa EMPRESA_ACTIVA.",
    )
    parser.add_argument(
        "--visibilidades",
        help="Public, Private o ambas separadas por coma.",
    )
    parser.add_argument("--tamano-maximo", type=int, default=1000)
    parser.add_argument("--solapamiento", type=int, default=150)
    argumentos = parser.parse_args()

    try:
        descubiertos = descubrir_conocimiento(
            empresa=argumentos.empresa,
            visibilidades=argumentos.visibilidades,
        )
        extraidos = extraer_documentos_markdown(descubiertos)
        resultados = [
            (
                documento,
                fragmentar_documento(
                    documento,
                    tamano_maximo=argumentos.tamano_maximo,
                    solapamiento=argumentos.solapamiento,
                ),
            )
            for documento in extraidos
        ]
    except (ErrorConfiguracion, ErrorExtraccionMarkdown, ErrorFragmentacion) as error:
        parser.error(str(error))

    if not resultados:
        print("No se encontraron documentos Markdown para fragmentar.")
        return

    total = sum(len(fragmentos) for _, fragmentos in resultados)
    print(f"Documentos fragmentados: {len(resultados)} | fragmentos: {total}")
    for documento, fragmentos in resultados:
        mayor = max(
            (len(fragmento.contenido_markdown) for fragmento in fragmentos),
            default=0,
        )
        print(
            f"- [{documento.visibilidad}] {documento.ruta_relativa} | "
            f"secciones: {len(documento.secciones)} | "
            f"fragmentos: {len(fragmentos)} | mayor: {mayor}"
        )


if __name__ == "__main__":
    main()
