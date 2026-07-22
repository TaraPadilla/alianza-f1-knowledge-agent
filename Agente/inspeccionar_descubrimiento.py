"""Permite inspeccionar el descubrimiento documental desde VS Code o terminal."""

from __future__ import annotations

import argparse

from app.configuracion import ErrorConfiguracion
from app.procesamiento import descubrir_conocimiento


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lista documentos soportados sin leer su contenido.",
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
        documentos = descubrir_conocimiento(
            empresa=argumentos.empresa,
            visibilidades=argumentos.visibilidades,
        )
    except ErrorConfiguracion as error:
        parser.error(str(error))

    if not documentos:
        print("No se encontraron documentos soportados.")
        return

    print(f"Documentos encontrados: {len(documentos)}")
    for documento in documentos:
        datos = documento.como_dict()
        print(
            f"- [{datos['visibilidad']}] "
            f"{datos['empresa']} | {datos['ruta_relativa']}"
        )


if __name__ == "__main__":
    main()
