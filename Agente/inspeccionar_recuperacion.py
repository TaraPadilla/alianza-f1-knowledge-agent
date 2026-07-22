"""Permite inspeccionar la recuperación semántica desde VS Code."""

from __future__ import annotations

import argparse

from app.configuracion import cargar_configuracion
from app.procesamiento.embeddings import (
    cargar_configuracion_embeddings,
    crear_proveedor_embeddings,
)
from app.recuperacion import FiltrosRecuperacion, recuperar_fragmentos


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consulta un índice vectorial sin generar una respuesta con LLM."
    )
    parser.add_argument("perfil", choices=("public", "internal"))
    parser.add_argument("pregunta")
    parser.add_argument("--empresa")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--visibilidad", choices=("Public", "Private"))
    parser.add_argument("--archivo", dest="ruta_relativa")
    parser.add_argument("--seccion", dest="titulo_seccion")
    parser.add_argument("--espera-maxima", type=float, default=45.0)
    return parser.parse_args()


def main() -> None:
    args = _argumentos()
    visibilidades = ("Public",) if args.perfil == "public" else ("Public", "Private")
    configuracion = cargar_configuracion(
        empresa=args.empresa,
        visibilidades=visibilidades,
    )
    configuracion_embeddings = cargar_configuracion_embeddings()
    proveedor = crear_proveedor_embeddings(
        configuracion_embeddings,
        max_reintentos_429=2,
        espera_maxima=args.espera_maxima,
    )
    resultados = recuperar_fragmentos(
        args.pregunta,
        args.perfil,
        configuracion_embeddings,
        proveedor,
        empresa=configuracion.empresa,
        top_k=args.top_k,
        filtros=FiltrosRecuperacion(
            visibilidad=args.visibilidad,
            ruta_relativa=args.ruta_relativa,
            titulo_seccion=args.titulo_seccion,
        ),
    )

    print(f"Empresa: {configuracion.empresa}")
    print(f"Perfil: {args.perfil}")
    print(f"Resultados: {len(resultados)}")
    print("Distancia: un valor menor significa mayor cercanía semántica.\n")
    for posicion, resultado in enumerate(resultados, start=1):
        vista_previa = resultado.contenido_markdown.replace("\n", " ")[:300]
        print(f"{posicion}. Distancia: {resultado.distancia:.6f}")
        print(f"   Visibilidad: {resultado.visibilidad}")
        print(f"   Documento: {resultado.ruta_relativa}")
        print(f"   Sección: {resultado.titulo_seccion or 'Sin encabezado'}")
        print(f"   Referencia: {resultado.referencia_fragmento}")
        print(f"   Contenido: {vista_previa}\n")


if __name__ == "__main__":
    main()
