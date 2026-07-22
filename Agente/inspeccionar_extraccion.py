"""Inspecciona la extracción documental sin mostrar contenido empresarial."""

from __future__ import annotations

import argparse

from app.configuracion import ErrorConfiguracion
from app.procesamiento import (
    ErrorExtraccionDocumento,
    descubrir_conocimiento,
    extraer_documentos,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resume la extracción sin imprimir contenido empresarial.",
    )
    parser.add_argument(
        "--empresa",
        help="Nombre de la empresa. Si se omite, se usa EMPRESA_ACTIVA.",
    )
    parser.add_argument(
        "--visibilidades",
        help="Public, Private o ambas separadas por coma.",
    )
    argumentos = parser.parse_args()

    try:
        descubiertos = descubrir_conocimiento(
            empresa=argumentos.empresa,
            visibilidades=argumentos.visibilidades,
        )
        extraidos = extraer_documentos(descubiertos)
    except (ErrorConfiguracion, ErrorExtraccionDocumento) as error:
        parser.error(str(error))

    if not extraidos:
        print("No se encontraron documentos soportados para extraer.")
        return

    print(f"Documentos extraídos: {len(extraidos)}")
    for documento in extraidos:
        caracteres = len(documento.contenido_markdown)
        print(
            f"- [{documento.visibilidad}] {documento.ruta_relativa} | "
            f"tipo: {documento.tipo_archivo} | "
            f"secciones: {len(documento.secciones)} | caracteres: {caracteres}"
        )


if __name__ == "__main__":
    main()
