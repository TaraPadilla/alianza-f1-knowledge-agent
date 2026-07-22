"""Orquestación sencilla de recuperación y generación para la interfaz."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from ..configuracion import cargar_configuracion
from ..generacion import (
    ConfiguracionLLM,
    ProveedorLLM,
    RespuestaGenerada,
    cargar_configuracion_llm,
    crear_proveedor_llm,
    generar_respuesta,
)
from ..procesamiento.embeddings import (
    ConfiguracionEmbeddings,
    ProveedorEmbeddings,
    cargar_configuracion_embeddings,
    crear_proveedor_embeddings,
)
from ..procesamiento.indice_vectorial import PerfilIndice
from ..recuperacion import FragmentoRecuperado, recuperar_fragmentos


@dataclass(frozen=True)
class ResultadoConsultaRAG:
    """Respuesta y datos de diagnóstico visibles en la interfaz."""

    empresa: str
    perfil: PerfilIndice
    modelo: str
    fragmentos: tuple[FragmentoRecuperado, ...]
    respuesta: RespuestaGenerada
    tiempo_total_segundos: float


class ServicioAgente:
    """Reúne dependencias del RAG sin acoplarlas a Streamlit."""

    def __init__(
        self,
        empresa: str,
        configuracion_embeddings: ConfiguracionEmbeddings,
        proveedor_embeddings: ProveedorEmbeddings,
        configuracion_llm: ConfiguracionLLM,
        proveedor_llm: ProveedorLLM,
    ) -> None:
        self.empresa = empresa
        self.configuracion_embeddings = configuracion_embeddings
        self.proveedor_embeddings = proveedor_embeddings
        self.configuracion_llm = configuracion_llm
        self.proveedor_llm = proveedor_llm

    def consultar(
        self,
        pregunta: str,
        perfil: PerfilIndice,
        *,
        top_k: int = 5,
    ) -> ResultadoConsultaRAG:
        """Mide el flujo completo desde la pregunta hasta la respuesta final."""

        inicio = perf_counter()
        fragmentos = recuperar_fragmentos(
            pregunta,
            perfil,
            self.configuracion_embeddings,
            self.proveedor_embeddings,
            empresa=self.empresa,
            top_k=top_k,
        )
        respuesta = generar_respuesta(
            pregunta,
            fragmentos,
            self.proveedor_llm,
        )
        return ResultadoConsultaRAG(
            empresa=self.empresa,
            perfil=perfil,
            modelo=self.configuracion_llm.modelo,
            fragmentos=tuple(fragmentos),
            respuesta=respuesta,
            tiempo_total_segundos=perf_counter() - inicio,
        )


def crear_servicio_agente(
    empresa: str | None = None,
    *,
    espera_maxima: float = 45.0,
) -> ServicioAgente:
    """Construye el servicio usando las variables existentes del proyecto."""

    configuracion_proyecto = cargar_configuracion(
        empresa=empresa,
        visibilidades=("Public", "Private"),
    )
    configuracion_embeddings = cargar_configuracion_embeddings()
    configuracion_llm = cargar_configuracion_llm()
    return ServicioAgente(
        empresa=configuracion_proyecto.empresa,
        configuracion_embeddings=configuracion_embeddings,
        proveedor_embeddings=crear_proveedor_embeddings(
            configuracion_embeddings,
            max_reintentos_429=2,
            espera_maxima=espera_maxima,
        ),
        configuracion_llm=configuracion_llm,
        proveedor_llm=crear_proveedor_llm(configuracion_llm),
    )
