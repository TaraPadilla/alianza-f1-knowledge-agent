"""Interfaz local del agente documental construida con Streamlit."""

from __future__ import annotations

from dataclasses import asdict
from html import escape
from uuid import uuid4

import streamlit as st

from Agente.app.configuracion import cargar_configuracion
from Agente.app.generacion import cargar_configuracion_llm
from Agente.app.servicios import (
    EXTENSIONES_SOPORTADAS,
    actualizar_conocimiento,
    crear_servicio_agente,
    guardar_documentos,
    listar_documentos,
    listar_empresas,
)


PREGUNTAS_SUGERIDAS = (
    "¿Cuáles son los principales servicios de la empresa?",
    "¿Qué tecnologías utiliza la empresa?",
    "¿Cómo es el proceso de trabajo?",
)
ETIQUETAS_PERFIL = {
    "public": "Public",
    "internal": "Internal (Public + Private)",
}


def _aplicar_estilos() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #f6f8fc; }
        .block-container { max-width: 1500px; padding-top: 1.2rem; }
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #e8ebf3;
        }
        .brand-banner {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 18px 22px;
            border-radius: 18px;
            color: white;
            background: linear-gradient(120deg, #101a34 0%, #17213c 70%, #26335d 100%);
            box-shadow: 0 12px 30px rgba(19, 31, 65, .16);
            margin-bottom: 18px;
        }
        .brand-icon {
            display: grid;
            place-items: center;
            width: 46px;
            height: 46px;
            border-radius: 14px;
            font-size: 25px;
            font-weight: 800;
            background: linear-gradient(145deg, #5368ff, #43c7ed);
        }
        .brand-title { font-size: 1.35rem; font-weight: 750; line-height: 1.1; }
        .brand-subtitle { color: #aebaff; margin-top: 4px; }
        [data-testid="stMetric"] {
            background: white;
            border: 1px solid #e7eaf2;
            border-radius: 14px;
            padding: 10px 14px;
            min-height: 92px;
        }
        [data-testid="stMetricValue"] > div {
            font-size: 1.12rem;
            line-height: 1.3;
            white-space: normal;
            overflow-wrap: anywhere;
        }
        [data-testid="stChatMessage"] {
            background: white;
            border: 1px solid #edf0f6;
            border-radius: 16px;
            padding: .25rem .6rem;
            margin-bottom: .65rem;
        }
        .documento {
            border: 1px solid #e8ebf3;
            border-radius: 12px;
            padding: 10px 12px;
            margin-bottom: 8px;
            background: #fbfcff;
        }
        .documento-nombre { color: #172033; font-weight: 650; }
        .documento-detalle { color: #78829b; font-size: .78rem; margin-top: 3px; }
        .fuente-rag {
            border-left: 3px solid #5368ff;
            padding: 7px 10px;
            margin: 6px 0;
            border-radius: 0 9px 9px 0;
            background: #f5f6ff;
            font-size: .88rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _formatear_tamano(tamano: int) -> str:
    if tamano < 1024:
        return f"{tamano} B"
    if tamano < 1024 * 1024:
        return f"{tamano / 1024:.1f} KB"
    return f"{tamano / (1024 * 1024):.1f} MB"


def _texto_sin_bloque_fuentes(texto: str) -> str:
    """La interfaz muestra las fuentes por separado, debajo de la respuesta."""

    return texto.split("\n\nFuentes:\n", maxsplit=1)[0]


def _inicializar_estado() -> None:
    st.session_state.setdefault("mensajes", [])
    st.session_state.setdefault("feedback", {})
    st.session_state.setdefault("contexto_chat", None)
    st.session_state.setdefault(
        "diagnostico",
        {"fragmentos": 0, "tiempo": None},
    )


@st.cache_resource(show_spinner=False)
def _obtener_servicio(empresa: str):
    return crear_servicio_agente(empresa)


def _sincronizar_contexto(empresa: str, perfil: str) -> None:
    contexto = (empresa, perfil)
    if st.session_state.contexto_chat != contexto:
        st.session_state.contexto_chat = contexto
        st.session_state.mensajes = []
        st.session_state.feedback = {}
        st.session_state.diagnostico = {"fragmentos": 0, "tiempo": None}


def _mostrar_documentos(empresa: str, visibilidad: str) -> None:
    documentos = listar_documentos(empresa, visibilidad)
    st.markdown(f"**Documentos ({visibilidad})** · {len(documentos)}")
    if not documentos:
        st.caption("Todavía no hay documentos en esta carpeta.")
        return
    for documento in documentos:
        st.markdown(
            (
                '<div class="documento">'
                f'<div class="documento-nombre">📄 {escape(documento.nombre)}</div>'
                '<div class="documento-detalle">'
                f"{_formatear_tamano(documento.tamano_bytes)} · {documento.visibilidad}"
                "</div></div>"
            ),
            unsafe_allow_html=True,
        )


def _panel_documentos(empresa: str) -> None:
    with st.sidebar:
        st.markdown("## Fuentes de conocimiento")
        st.caption("Carga y actualiza los documentos de la empresa.")
        visibilidad = st.radio(
            "Ubicación del documento",
            ("Public", "Private"),
            horizontal=True,
        )
        archivos = st.file_uploader(
            f"Subir documentos a {visibilidad}",
            type=list(EXTENSIONES_SOPORTADAS),
            accept_multiple_files=True,
            help="Actualmente se admite Markdown. Los demás formatos se agregarán por módulos.",
        )

        columna_subir, columna_indice = st.columns(2)
        with columna_subir:
            guardar = st.button(
                "Guardar",
                type="primary",
                use_container_width=True,
                disabled=not archivos,
            )
        with columna_indice:
            procesar = st.button(
                "Actualizar índice",
                use_container_width=True,
            )

        if guardar:
            try:
                guardados = guardar_documentos(archivos, empresa, visibilidad)
                st.toast(
                    f"{len(guardados)} documento(s) guardado(s).",
                    icon="✅",
                )
                st.rerun()
            except ValueError as error:
                st.error(str(error))

        if procesar:
            try:
                with st.status(
                    "Actualizando conocimiento...",
                    expanded=True,
                ) as estado:

                    def progreso(perfil, actual, total, accion, referencia):
                        estado.write(
                            f"{perfil}: {actual}/{total} · {accion} · {referencia}"
                        )

                    resultados = actualizar_conocimiento(
                        empresa,
                        visibilidad,
                        progreso=progreso,
                    )
                    for resultado in resultados:
                        estado.write(
                            f"{resultado.perfil}: "
                            f"{resultado.cantidad_fragmentos} fragmentos; "
                            f"{resultado.eliminados} obsoletos eliminados."
                        )
                    estado.update(
                        label="Conocimiento actualizado",
                        state="complete",
                        expanded=False,
                    )
            except Exception as error:  # Streamlit debe mostrar el error del pipeline.
                st.error(f"No fue posible actualizar el índice: {error}")

        st.divider()
        _mostrar_documentos(empresa, visibilidad)
        st.caption(
            "No se muestra un estado por archivo: la actualización se controla "
            "como una operación completa."
        )


def _mostrar_fuentes(fuentes: list[dict]) -> None:
    if not fuentes:
        return
    st.caption("Fuentes utilizadas")
    for fuente in fuentes:
        st.markdown(
            (
                '<div class="fuente-rag">'
                f"📄 <strong>{escape(fuente['archivo'])}</strong><br>"
                f"Sección: {escape(fuente['seccion'])}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def _mostrar_chat() -> None:
    with st.container(height=510, border=True):
        if not st.session_state.mensajes:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(
                    "¡Hola! Soy el asistente documental de la empresa.  \n"
                    "¿En qué puedo ayudarte?"
                )

        for mensaje in st.session_state.mensajes:
            avatar = "👤" if mensaje["rol"] == "user" else "🤖"
            with st.chat_message(mensaje["rol"], avatar=avatar):
                st.markdown(mensaje["texto"])
                if mensaje["rol"] == "assistant":
                    _mostrar_fuentes(mensaje.get("fuentes", []))
                    valor = st.feedback(
                        "thumbs",
                        key=f"feedback_{mensaje['id']}",
                    )
                    if valor is not None:
                        st.session_state.feedback[mensaje["id"]] = valor


def main() -> None:
    st.set_page_config(
        page_title="Alianza F1 Knowledge Agent",
        page_icon="🔷",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _aplicar_estilos()
    _inicializar_estado()

    empresas = listar_empresas()
    if not empresas:
        st.error("No se encontraron empresas con carpetas Public y Private.")
        st.stop()
    empresa_activa = cargar_configuracion().empresa

    st.markdown(
        """
        <div class="brand-banner">
            <div class="brand-icon">A</div>
            <div>
                <div class="brand-title">Alianza F1</div>
                <div class="brand-subtitle">Knowledge Agent</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    columna_empresa, columna_perfil = st.columns((1, 2))
    with columna_empresa:
        empresa = st.selectbox(
            "Empresa",
            empresas,
            index=empresas.index(empresa_activa) if empresa_activa in empresas else 0,
        )
    with columna_perfil:
        perfil = st.radio(
            "Perfil de consulta",
            ("public", "internal"),
            format_func=ETIQUETAS_PERFIL.get,
            horizontal=True,
        )

    _sincronizar_contexto(empresa, perfil)
    _panel_documentos(empresa)
    modelo = cargar_configuracion_llm().modelo
    diagnostico = st.session_state.diagnostico

    st.markdown("### Chat del agente")
    st.caption("Pregunta sobre la información contenida en los documentos.")
    metricas = st.columns(5)
    valores = (
        ("Empresa", empresa),
        ("Perfil", ETIQUETAS_PERFIL[perfil]),
        ("Modelo", modelo),
        ("Fragmentos", str(diagnostico["fragmentos"])),
        (
            "Tiempo total",
            f"{diagnostico['tiempo']:.2f} s"
            if diagnostico["tiempo"] is not None
            else "—",
        ),
    )
    for columna, (etiqueta, valor) in zip(metricas, valores, strict=True):
        columna.metric(etiqueta, valor)

    _mostrar_chat()

    st.caption("Preguntas sugeridas")
    columnas = st.columns(len(PREGUNTAS_SUGERIDAS))
    pregunta_sugerida = None
    for columna, sugerencia in zip(columnas, PREGUNTAS_SUGERIDAS, strict=True):
        if columna.button(sugerencia, use_container_width=True):
            pregunta_sugerida = sugerencia

    pregunta_escrita = st.chat_input("Escribe tu pregunta aquí...")
    pregunta = pregunta_sugerida or pregunta_escrita
    if pregunta:
        st.session_state.mensajes.append(
            {"id": str(uuid4()), "rol": "user", "texto": pregunta}
        )
        try:
            with st.spinner("Consultando los documentos..."):
                resultado = _obtener_servicio(empresa).consultar(
                    pregunta,
                    perfil,
                    top_k=5,
                )
            st.session_state.mensajes.append(
                {
                    "id": str(uuid4()),
                    "rol": "assistant",
                    "texto": _texto_sin_bloque_fuentes(resultado.respuesta.texto),
                    "fuentes": [
                        asdict(fuente) for fuente in resultado.respuesta.fuentes
                    ],
                }
            )
            st.session_state.diagnostico = {
                "fragmentos": len(resultado.fragmentos),
                "tiempo": resultado.tiempo_total_segundos,
            }
        except Exception as error:
            st.session_state.mensajes.append(
                {
                    "id": str(uuid4()),
                    "rol": "assistant",
                    "texto": f"No fue posible completar la consulta: {error}",
                    "fuentes": [],
                }
            )
        st.rerun()


if __name__ == "__main__":
    main()
