"""Configuración centralizada de infraestructura y operación del agente."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from dotenv import dotenv_values


VISIBILIDADES_VALIDAS = ("Public", "Private")
RAIZ_AGENTE = Path(__file__).resolve().parents[1]
NOMBRE_CONFIGURACION_OPERATIVA = "configuracion_operativa.json"
CLAVES_OPERATIVAS = (
    "EMPRESA_ACTIVA",
    "VISIBILIDADES_PERMITIDAS",
    "LLM_MODEL",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSIONS",
)
VALORES_PREDETERMINADOS: dict[str, object] = {
    "EMPRESA_ACTIVA": "",
    "VISIBILIDADES_PERMITIDAS": ("Public", "Private"),
    "LLM_MODEL": "gemini-2.5-flash",
    "EMBEDDING_MODEL": "models/gemini-embedding-001",
    "EMBEDDING_DIMENSIONS": 3072,
}


class ErrorConfiguracion(ValueError):
    """Indica que la configuración del agente no es válida."""


@dataclass(frozen=True)
class ConfiguracionOperativa:
    """Valores persistentes que un administrador puede modificar."""

    empresa_activa: str
    visibilidades_permitidas: tuple[str, ...]
    llm_model: str
    embedding_model: str
    embedding_dimensiones: int
    reindexacion_pendiente: bool = False


@dataclass(frozen=True)
class Configuracion:
    """Valores validados que utiliza el pipeline documental."""

    empresa: str
    visibilidades: tuple[str, ...]
    raiz_agente: Path

    @property
    def ruta_empresa(self) -> Path:
        return self.raiz_agente / self.empresa

    @property
    def rutas_conocimiento(self) -> tuple[Path, ...]:
        return tuple(self.ruta_empresa / nivel for nivel in self.visibilidades)


def ruta_configuracion_operativa(raiz_agente: Path | None = None) -> Path:
    """Devuelve la ubicación portable del archivo operativo."""

    raiz = (raiz_agente or RAIZ_AGENTE).resolve()
    return raiz / "config" / NOMBRE_CONFIGURACION_OPERATIVA


def _leer_archivo_env(ruta_env: Path) -> dict[str, str]:
    """Lee el .env solo como fuente inicial e infraestructura local."""

    if not ruta_env.is_file():
        return {}
    return {
        clave: valor
        for clave, valor in dotenv_values(ruta_env).items()
        if isinstance(valor, str)
    }


def obtener_valor_infraestructura(
    nombre: str,
    *,
    raiz_agente: Path | None = None,
    ruta_env: Path | None = None,
) -> str:
    """Lee secretos e infraestructura desde el entorno o el archivo .env."""

    raiz = (raiz_agente or RAIZ_AGENTE).resolve()
    archivo_env = ruta_env or (raiz / ".env")
    valor = os.getenv(nombre) or _leer_archivo_env(archivo_env).get(nombre, "")
    return valor.strip()


def _normalizar_visibilidades(
    visibilidades: str | Iterable[str] | None,
) -> tuple[str, ...]:
    if visibilidades is None:
        elementos = list(VISIBILIDADES_VALIDAS)
    elif isinstance(visibilidades, str):
        elementos = visibilidades.split(",")
    else:
        elementos = list(visibilidades)

    canonicas = {nivel.casefold(): nivel for nivel in VISIBILIDADES_VALIDAS}
    resultado: list[str] = []
    for elemento in elementos:
        clave = str(elemento).strip().casefold()
        if not clave:
            continue
        if clave not in canonicas:
            raise ErrorConfiguracion(
                f"Visibilidad desconocida: '{elemento}'. Valores permitidos: "
                + ", ".join(VISIBILIDADES_VALIDAS)
                + "."
            )
        nivel = canonicas[clave]
        if nivel not in resultado:
            resultado.append(nivel)
    if not resultado:
        raise ErrorConfiguracion("Debe indicarse al menos un nivel de visibilidad.")
    return tuple(resultado)


def _normalizar_booleano(valor: object) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        normalizado = valor.strip().casefold()
        if normalizado in {"true", "1", "si", "sí"}:
            return True
        if normalizado in {"false", "0", "no", ""}:
            return False
    raise ErrorConfiguracion("REINDEXACION_PENDIENTE debe ser true o false.")


def _normalizar_operativa(valores: Mapping[str, object]) -> ConfiguracionOperativa:
    try:
        dimensiones = int(valores["EMBEDDING_DIMENSIONS"])
    except (KeyError, TypeError, ValueError) as error:
        raise ErrorConfiguracion(
            "EMBEDDING_DIMENSIONS debe ser un número entero."
        ) from error
    if dimensiones <= 0:
        raise ErrorConfiguracion("EMBEDDING_DIMENSIONS debe ser mayor que cero.")

    llm_model = str(valores.get("LLM_MODEL", "")).strip()
    embedding_model = str(valores.get("EMBEDDING_MODEL", "")).strip()
    if not llm_model:
        raise ErrorConfiguracion("LLM_MODEL no puede estar vacío.")
    if not embedding_model:
        raise ErrorConfiguracion("EMBEDDING_MODEL no puede estar vacío.")

    return ConfiguracionOperativa(
        empresa_activa=str(valores.get("EMPRESA_ACTIVA", "")).strip(),
        visibilidades_permitidas=_normalizar_visibilidades(
            valores.get("VISIBILIDADES_PERMITIDAS")
        ),
        llm_model=llm_model,
        embedding_model=embedding_model,
        embedding_dimensiones=dimensiones,
        reindexacion_pendiente=_normalizar_booleano(
            valores.get("REINDEXACION_PENDIENTE", False)
        ),
    )


def _serializar_operativa(
    configuracion: ConfiguracionOperativa,
) -> dict[str, object]:
    return {
        "EMPRESA_ACTIVA": configuracion.empresa_activa,
        "VISIBILIDADES_PERMITIDAS": list(
            configuracion.visibilidades_permitidas
        ),
        "LLM_MODEL": configuracion.llm_model,
        "EMBEDDING_MODEL": configuracion.embedding_model,
        "EMBEDDING_DIMENSIONS": configuracion.embedding_dimensiones,
        "REINDEXACION_PENDIENTE": configuracion.reindexacion_pendiente,
    }


def _escribir_json_atomico(ruta: Path, datos: Mapping[str, object]) -> None:
    """Escribe dentro del directorio montado y reemplaza el archivo al final."""

    ruta.parent.mkdir(parents=True, exist_ok=True)
    descriptor, nombre_temporal = tempfile.mkstemp(
        prefix=f".{ruta.name}.",
        suffix=".tmp",
        dir=ruta.parent,
    )
    temporal = Path(nombre_temporal)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, ruta)
    finally:
        if temporal.exists():
            temporal.unlink()


def _valores_iniciales(
    archivo_env: Path,
) -> dict[str, object]:
    """Migra una sola vez los valores operativos del entorno o .env actual."""

    valores_archivo = _leer_archivo_env(archivo_env)
    resultado: dict[str, object] = {}
    for clave, predeterminado in VALORES_PREDETERMINADOS.items():
        resultado[clave] = (
            os.getenv(clave)
            or valores_archivo.get(clave)
            or predeterminado
        )
    resultado["REINDEXACION_PENDIENTE"] = False
    return resultado


def cargar_configuracion_operativa(
    *,
    raiz_agente: Path | None = None,
    ruta_env: Path | None = None,
    ruta_configuracion: Path | None = None,
) -> ConfiguracionOperativa:
    """Carga la configuración persistente y la inicializa cuando no existe.

    La prioridad por clave es: archivo persistente, entorno/.env y valor
    predeterminado. El .env solo participa en la migración inicial.
    """

    raiz = (raiz_agente or RAIZ_AGENTE).resolve()
    archivo_env = ruta_env or (raiz / ".env")
    archivo_configuracion = ruta_configuracion or ruta_configuracion_operativa(raiz)

    if archivo_configuracion.is_file():
        try:
            datos_persistidos = json.loads(
                archivo_configuracion.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise ErrorConfiguracion(
                f"La configuración operativa {archivo_configuracion} no es válida."
            ) from error
        if not isinstance(datos_persistidos, dict):
            raise ErrorConfiguracion(
                "La configuración operativa debe ser un objeto JSON."
            )
        valores = _valores_iniciales(archivo_env)
        valores.update(datos_persistidos)
    else:
        valores = _valores_iniciales(archivo_env)

    configuracion = _normalizar_operativa(valores)
    datos_normalizados = _serializar_operativa(configuracion)
    if not archivo_configuracion.is_file() or datos_persistidos != datos_normalizados:
        _escribir_json_atomico(archivo_configuracion, datos_normalizados)
    return configuracion


def actualizar_configuracion_operativa(
    cambios: Mapping[str, object],
    *,
    raiz_agente: Path | None = None,
    ruta_env: Path | None = None,
    ruta_configuracion: Path | None = None,
) -> ConfiguracionOperativa:
    """Persiste cambios administrativos sin modificar el archivo .env."""

    desconocidas = set(cambios).difference(CLAVES_OPERATIVAS)
    if desconocidas:
        raise ErrorConfiguracion(
            "Configuraciones operativas desconocidas: "
            + ", ".join(sorted(desconocidas))
            + "."
        )

    raiz = (raiz_agente or RAIZ_AGENTE).resolve()
    archivo_configuracion = ruta_configuracion or ruta_configuracion_operativa(raiz)
    actual = cargar_configuracion_operativa(
        raiz_agente=raiz,
        ruta_env=ruta_env,
        ruta_configuracion=archivo_configuracion,
    )
    valores = _serializar_operativa(actual)
    cambio_embeddings = any(
        clave in cambios
        and str(cambios[clave]).strip()
        != str(valores[clave]).strip()
        for clave in ("EMBEDDING_MODEL", "EMBEDDING_DIMENSIONS")
    )
    valores.update(cambios)
    if cambio_embeddings:
        valores["REINDEXACION_PENDIENTE"] = True

    configuracion = _normalizar_operativa(valores)
    _escribir_json_atomico(
        archivo_configuracion,
        _serializar_operativa(configuracion),
    )
    return configuracion


def confirmar_reindexacion_operativa(
    *,
    raiz_agente: Path | None = None,
    ruta_env: Path | None = None,
    ruta_configuracion: Path | None = None,
) -> ConfiguracionOperativa:
    """Habilita la configuración nueva después de reconstruir ambos índices."""

    raiz = (raiz_agente or RAIZ_AGENTE).resolve()
    archivo_configuracion = ruta_configuracion or ruta_configuracion_operativa(raiz)
    actual = cargar_configuracion_operativa(
        raiz_agente=raiz,
        ruta_env=ruta_env,
        ruta_configuracion=archivo_configuracion,
    )
    valores = _serializar_operativa(actual)
    valores["REINDEXACION_PENDIENTE"] = False
    configuracion = _normalizar_operativa(valores)
    _escribir_json_atomico(
        archivo_configuracion,
        _serializar_operativa(configuracion),
    )
    return configuracion


def _validar_empresa(empresa: str | None, raiz_agente: Path) -> str:
    nombre = (empresa or "").strip()
    if not nombre:
        raise ErrorConfiguracion(
            "No se indicó una empresa. Define EMPRESA_ACTIVA en la "
            "configuración operativa."
        )
    if nombre in {".", ".."} or Path(nombre).name != nombre:
        raise ErrorConfiguracion(
            "EMPRESA_ACTIVA debe contener solo el nombre de la empresa, no una ruta."
        )
    if not (raiz_agente / nombre).is_dir():
        raise ErrorConfiguracion(
            f"No existe la carpeta de la empresa '{nombre}' dentro de {raiz_agente}."
        )
    return nombre


def cargar_configuracion(
    empresa: str | None = None,
    visibilidades: str | Iterable[str] | None = None,
    *,
    raiz_agente: Path | None = None,
    ruta_env: Path | None = None,
    ruta_configuracion: Path | None = None,
) -> Configuracion:
    """Carga empresa y visibilidades desde la configuración operativa."""

    raiz = (raiz_agente or RAIZ_AGENTE).resolve()
    operativa = cargar_configuracion_operativa(
        raiz_agente=raiz,
        ruta_env=ruta_env,
        ruta_configuracion=ruta_configuracion,
    )
    empresa_validada = _validar_empresa(
        empresa or operativa.empresa_activa,
        raiz,
    )
    niveles = _normalizar_visibilidades(
        visibilidades
        if visibilidades is not None
        else operativa.visibilidades_permitidas
    )
    for nivel in niveles:
        if not (raiz / empresa_validada / nivel).is_dir():
            raise ErrorConfiguracion(
                f"La empresa '{empresa_validada}' no tiene la carpeta requerida "
                f"'{nivel}'."
            )
    return Configuracion(
        empresa=empresa_validada,
        visibilidades=niveles,
        raiz_agente=raiz,
    )
