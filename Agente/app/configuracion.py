"""Configuración portable para seleccionar empresa y fuentes de conocimiento."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dotenv import dotenv_values, set_key


VISIBILIDADES_VALIDAS = ("Public", "Private")
RAIZ_AGENTE = Path(__file__).resolve().parents[1]


class ErrorConfiguracion(ValueError):
    """Indica que la empresa o sus niveles de visibilidad no son válidos."""


@dataclass(frozen=True)
class Configuracion:
    """Valores validados que utilizará el pipeline de procesamiento."""

    empresa: str
    visibilidades: tuple[str, ...]
    raiz_agente: Path

    @property
    def ruta_empresa(self) -> Path:
        """Devuelve la carpeta de la empresa activa."""

        return self.raiz_agente / self.empresa

    @property
    def rutas_conocimiento(self) -> tuple[Path, ...]:
        """Devuelve las carpetas Public y/o Private habilitadas."""

        return tuple(self.ruta_empresa / nivel for nivel in self.visibilidades)


def _leer_archivo_env(ruta_env: Path) -> dict[str, str]:
    """Lee el archivo .env sin modificar globalmente el entorno de Python."""

    if not ruta_env.is_file():
        return {}

    valores = dotenv_values(ruta_env)
    return {
        clave: valor
        for clave, valor in valores.items()
        if isinstance(valor, str)
    }


def actualizar_valor_env(ruta_env: Path, clave: str, valor: str) -> None:
    """Actualiza un valor específico en el archivo .env."""

    if not ruta_env.is_file():
        raise ValueError(f"El archivo {ruta_env} no existe.")

    set_key(ruta_env, clave, valor)


def _obtener_valor(
    nombre: str,
    valores_archivo: dict[str, str],
) -> str | None:
    """Da prioridad al entorno del sistema sobre el archivo .env."""

    return os.getenv(nombre) or valores_archivo.get(nombre)


def _validar_empresa(empresa: str | None, raiz_agente: Path) -> str:
    """Valida el nombre y comprueba que la empresa exista dentro de Agente."""

    nombre = (empresa or "").strip()
    if not nombre:
        raise ErrorConfiguracion(
            "No se indicó una empresa. Usa el parámetro 'empresa' o define "
            "EMPRESA_ACTIVA en Agente/.env."
        )

    # Solo se acepta un nombre de carpeta, nunca una ruta absoluta o relativa.
    if nombre in {".", ".."} or Path(nombre).name != nombre:
        raise ErrorConfiguracion(
            "EMPRESA_ACTIVA debe contener solo el nombre de la empresa, no una ruta."
        )

    ruta_empresa = raiz_agente / nombre
    if not ruta_empresa.is_dir():
        raise ErrorConfiguracion(
            f"No existe la carpeta de la empresa '{nombre}' dentro de {raiz_agente}."
        )

    return nombre


def _normalizar_visibilidades(
    visibilidades: str | Iterable[str] | None,
) -> tuple[str, ...]:
    """Normaliza los niveles y rechaza valores distintos de Public o Private."""

    if visibilidades is None:
        elementos = list(VISIBILIDADES_VALIDAS)
    elif isinstance(visibilidades, str):
        elementos = visibilidades.split(",")
    else:
        elementos = list(visibilidades)

    nombres_canonicos = {nivel.lower(): nivel for nivel in VISIBILIDADES_VALIDAS}
    resultado: list[str] = []

    for elemento in elementos:
        clave = elemento.strip().lower()
        if not clave:
            continue
        if clave not in nombres_canonicos:
            permitidas = ", ".join(VISIBILIDADES_VALIDAS)
            raise ErrorConfiguracion(
                f"Visibilidad desconocida: '{elemento}'. Valores permitidos: {permitidas}."
            )

        nivel = nombres_canonicos[clave]
        if nivel not in resultado:
            resultado.append(nivel)

    if not resultado:
        raise ErrorConfiguracion("Debe indicarse al menos un nivel de visibilidad.")

    return tuple(resultado)


def cargar_configuracion(
    empresa: str | None = None,
    visibilidades: str | Iterable[str] | None = None,
    *,
    raiz_agente: Path | None = None,
    ruta_env: Path | None = None,
) -> Configuracion:
    """Carga y valida la empresa activa y las fuentes que se pueden consultar.

    La empresa recibida como parámetro tiene prioridad. Si no se proporciona,
    se consulta EMPRESA_ACTIVA en el entorno y luego en el archivo ``.env``.
    No existe una empresa predeterminada: su ausencia siempre produce un error.
    """

    raiz = (raiz_agente or RAIZ_AGENTE).resolve()
    archivo_env = ruta_env or (raiz / ".env")
    valores_archivo = _leer_archivo_env(archivo_env)

    empresa_solicitada = empresa or _obtener_valor(
        "EMPRESA_ACTIVA",
        valores_archivo,
    )

    if visibilidades is None:
        visibilidades = _obtener_valor(
            "VISIBILIDADES_PERMITIDAS",
            valores_archivo,
        )

    empresa_validada = _validar_empresa(empresa_solicitada, raiz)
    niveles = _normalizar_visibilidades(visibilidades)

    # Detectar pronto una estructura incompleta produce errores más comprensibles.
    for nivel in niveles:
        ruta_nivel = raiz / empresa_validada / nivel
        if not ruta_nivel.is_dir():
            raise ErrorConfiguracion(
                f"La empresa '{empresa_validada}' no tiene la carpeta requerida '{nivel}'."
            )

    return Configuracion(
        empresa=empresa_validada,
        visibilidades=niveles,
        raiz_agente=raiz,
    )
