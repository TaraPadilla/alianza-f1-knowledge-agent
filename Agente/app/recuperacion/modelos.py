"""Modelos sencillos para consultas y resultados de recuperación."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FiltrosRecuperacion:
    """Filtros exactos aplicables sobre metadatos existentes en Chroma."""

    visibilidad: str | None = None
    ruta_relativa: str | None = None
    titulo_seccion: str | None = None


@dataclass(frozen=True)
class FragmentoRecuperado:
    """Fragmento ordenado por cercanía semántica y con su procedencia."""

    contenido_markdown: str
    distancia: float
    empresa: str
    visibilidad: str
    ruta_relativa: str
    titulo_seccion: str | None
    nivel_seccion: int
    indice_seccion: int
    indice_fragmento_seccion: int
    total_fragmentos_seccion: int
    indice_fragmento_documento: int
    referencia_fragmento: str
    tipo_archivo: str = "markdown"
    archivo_original: str = ""
    pagina: int | None = None

    @classmethod
    def desde_chroma(
        cls,
        contenido_markdown: str,
        distancia: float,
        metadatos: dict,
    ) -> "FragmentoRecuperado":
        """Convierte la respuesta escalar de Chroma al modelo del proyecto."""

        titulo = metadatos.get("titulo_seccion")
        pagina = metadatos.get("pagina")
        return cls(
            contenido_markdown=contenido_markdown,
            distancia=float(distancia),
            empresa=str(metadatos["empresa"]),
            visibilidad=str(metadatos["visibilidad"]),
            ruta_relativa=str(metadatos["ruta_relativa"]),
            titulo_seccion=str(titulo) if titulo not in {None, ""} else None,
            nivel_seccion=int(metadatos["nivel_seccion"]),
            indice_seccion=int(metadatos["indice_seccion"]),
            indice_fragmento_seccion=int(
                metadatos["indice_fragmento_seccion"]
            ),
            total_fragmentos_seccion=int(
                metadatos["total_fragmentos_seccion"]
            ),
            indice_fragmento_documento=int(
                metadatos["indice_fragmento_documento"]
            ),
            referencia_fragmento=str(metadatos["referencia_fragmento"]),
            tipo_archivo=str(metadatos.get("tipo_archivo") or "markdown"),
            archivo_original=str(metadatos.get("archivo_original") or ""),
            pagina=int(pagina) if pagina not in {None, ""} else None,
        )
