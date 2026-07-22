"""Estructuras de datos compartidas por las etapas de procesamiento."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DocumentoDescubierto:
    """Describe un archivo localizado sin leer ni modificar su contenido."""

    empresa: str
    visibilidad: str
    ruta_relativa: str
    # La ruta local permite abrir el archivo en la etapa siguiente, pero no debe
    # incluirse en metadatos, respuestas ni registros que puedan publicarse.
    ruta_archivo: Path = field(repr=False)

    def como_dict(self) -> dict[str, str]:
        """Devuelve solamente la información portable y segura para inspección."""

        return {
            "empresa": self.empresa,
            "visibilidad": self.visibilidad,
            "ruta_relativa": self.ruta_relativa,
        }


@dataclass(frozen=True)
class SeccionMarkdown:
    """Sección normalizada a Markdown, sin importar el formato de origen."""

    titulo: str | None
    nivel: int
    contenido_markdown: str
    pagina: int | None = None


@dataclass(frozen=True)
class DocumentoExtraido:
    """Contenido Markdown leído y separado, con su procedencia original."""

    empresa: str
    visibilidad: str
    ruta_relativa: str
    secciones: tuple[SeccionMarkdown, ...]
    tipo_archivo: str = "markdown"
    archivo_original: str = ""

    @property
    def contenido_markdown(self) -> str:
        """Reúne las secciones sin convertirlas a texto plano."""

        return "\n\n".join(
            seccion.contenido_markdown for seccion in self.secciones
        )


@dataclass(frozen=True)
class FragmentoMarkdown:
    """Fragmento listo para una etapa posterior de vectorización."""

    contenido_markdown: str
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

    def metadatos(self) -> dict[str, str | int | None]:
        """Devuelve la procedencia del fragmento sin rutas locales."""

        return {
            "empresa": self.empresa,
            "visibilidad": self.visibilidad,
            "ruta_relativa": self.ruta_relativa,
            "tipo_archivo": self.tipo_archivo,
            "archivo_original": self.archivo_original,
            "titulo_seccion": self.titulo_seccion,
            "pagina": self.pagina,
            "nivel_seccion": self.nivel_seccion,
            "indice_seccion": self.indice_seccion,
            "indice_fragmento_seccion": self.indice_fragmento_seccion,
            "total_fragmentos_seccion": self.total_fragmentos_seccion,
            "indice_fragmento_documento": self.indice_fragmento_documento,
            "referencia_fragmento": self.referencia_fragmento,
        }
