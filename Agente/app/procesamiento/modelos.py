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
