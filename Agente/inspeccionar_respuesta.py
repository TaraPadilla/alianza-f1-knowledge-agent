"""Ejecuta recuperación y generación desde VS Code o la terminal."""

from __future__ import annotations

import argparse

from app.configuracion import cargar_configuracion
from app.generacion import (
    cargar_configuracion_llm,
    crear_proveedor_llm,
    generar_respuesta,
)
from app.procesamiento.embeddings import (
    cargar_configuracion_embeddings,
    crear_proveedor_embeddings,
)
from app.recuperacion import FiltrosRecuperacion, recuperar_fragmentos


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Responde usando exclusivamente el índice documental local."
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
    proveedor_embeddings = crear_proveedor_embeddings(
        configuracion_embeddings,
        max_reintentos_429=2,
        espera_maxima=args.espera_maxima,
    )
    fragmentos = recuperar_fragmentos(
        args.pregunta,
        args.perfil,
        configuracion_embeddings,
        proveedor_embeddings,
        empresa=configuracion.empresa,
        top_k=args.top_k,
        filtros=FiltrosRecuperacion(
            visibilidad=args.visibilidad,
            ruta_relativa=args.ruta_relativa,
            titulo_seccion=args.titulo_seccion,
        ),
    )

    proveedor_llm = crear_proveedor_llm(cargar_configuracion_llm())
    respuesta = generar_respuesta(args.pregunta, fragmentos, proveedor_llm)

    print(f"Empresa: {configuracion.empresa}")
    print(f"Perfil: {args.perfil}")
    print(f"Fragmentos recuperados: {len(fragmentos)}")
    if fragmentos:
        print("Distancia: un valor menor significa mayor cercanía semántica.")
        for posicion, fragmento in enumerate(fragmentos, start=1):
            print(f"  {posicion}. {fragmento.distancia:.6f}")
    print("\nRespuesta:\n")
    print(respuesta.texto)


if __name__ == "__main__":
    main()
