"""Servicios que conectan el pipeline con interfaces y scripts."""

from .agente import ResultadoConsultaRAG, ServicioAgente, crear_servicio_agente
from .documentos import (
    EXTENSIONES_CARGADOR,
    EXTENSIONES_SOPORTADAS,
    DocumentoInterfaz,
    eliminar_documento,
    guardar_documentos,
    listar_documentos,
    listar_empresas,
)
from .indexacion import (
    actualizar_conocimiento,
    obtener_cantidad_fragmentos,
    obtener_estado_indexacion,
    obtener_fecha_ultima_indexacion,
)

__all__ = [
    "EXTENSIONES_SOPORTADAS",
    "EXTENSIONES_CARGADOR",
    "DocumentoInterfaz",
    "ResultadoConsultaRAG",
    "ServicioAgente",
    "actualizar_conocimiento",
    "crear_servicio_agente",
    "eliminar_documento",
    "guardar_documentos",
    "listar_documentos",
    "listar_empresas",
    "obtener_cantidad_fragmentos",
    "obtener_estado_indexacion",
    "obtener_fecha_ultima_indexacion",
]
