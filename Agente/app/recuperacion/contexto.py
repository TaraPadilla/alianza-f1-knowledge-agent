"""Ensamblaje del contexto que usará una futura etapa de generación."""

from __future__ import annotations

from .modelos import FragmentoRecuperado


def ensamblar_contexto(resultados: list[FragmentoRecuperado]) -> str:
    """Une fragmentos Markdown con referencias legibles y sin rutas locales."""

    bloques: list[str] = []
    for posicion, fragmento in enumerate(resultados, start=1):
        seccion = fragmento.titulo_seccion or "Sin encabezado"
        ubicacion = (
            f"Página: {fragmento.pagina}"
            if fragmento.pagina is not None
            else f"Sección: {seccion}"
        )
        bloques.append(
            "\n".join(
                (
                    f"[Fuente {posicion}]",
                    f"Empresa: {fragmento.empresa}",
                    f"Visibilidad: {fragmento.visibilidad}",
                    f"Documento: {fragmento.ruta_relativa}",
                    f"Tipo: {fragmento.tipo_archivo}",
                    ubicacion,
                    f"Referencia: {fragmento.referencia_fragmento}",
                    "Contenido:",
                    fragmento.contenido_markdown,
                )
            )
        )
    return "\n\n---\n\n".join(bloques)
