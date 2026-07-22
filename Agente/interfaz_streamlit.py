"""Interfaz local del agente documental construida con Streamlit."""

from __future__ import annotations

from dataclasses import asdict
from html import escape
from uuid import uuid4

import streamlit as st

from Agente.app.configuracion import (
    RAIZ_AGENTE,
    actualizar_valor_env,
    cargar_configuracion,
)
from Agente.app.generacion import cargar_configuracion_llm, probar_modelo
from Agente.app.servicios import (
    EXTENSIONES_CARGADOR,
    EXTENSIONES_SOPORTADAS,
    actualizar_conocimiento,
    crear_servicio_agente,
    eliminar_documento,
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
        :root {
            --fondo: #040711;
            --panel: rgba(10, 17, 36, .88);
            --panel-fuerte: #0a1124;
            --borde: rgba(91, 224, 255, .18);
            --cian: #54e6ff;
            --violeta: #9b7cff;
            --verde: #55efbd;
            --texto: #edf7ff;
            --texto-suave: #91a8c7;
        }
        html, body, [class*="css"] { color: var(--texto); }
        .stApp {
            background:
                radial-gradient(circle at 78% 2%, rgba(67, 63, 184, .22), transparent 31%),
                radial-gradient(circle at 18% 92%, rgba(0, 184, 219, .12), transparent 28%),
                var(--fondo);
        }
        header[data-testid="stHeader"] {
            display: block;
            height: 0;
            min-height: 0;
            background: transparent;
            pointer-events: none;
        }
        [data-testid="stToolbar"], #MainMenu, footer { display: none !important; }
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
            display: none !important;
        }
        .block-container {
            max-width: none;
            padding: .3rem .5rem .5rem;
        }
        [data-testid="stSidebar"] {
            display: block !important;
            width: 280px !important;
            min-width: 280px !important;
            max-width: 280px !important;
            margin-left: 0 !important;
            transform: none !important;
            visibility: visible !important;
            background:
                linear-gradient(180deg, rgba(15, 25, 53, .98), rgba(5, 10, 24, .98));
            border-right: 1px solid var(--borde);
            box-shadow: 18px 0 50px rgba(0, 0, 0, .22);
        }
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0;
        }
        [data-testid="stSidebarHeader"],
        [data-testid="stLogoSpacer"] {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
        }
        [data-testid="stSidebarUserContent"] {
            padding-top: .3rem !important;
            margin-top: 0 !important;
        }
        [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] {
            gap: .55rem;
        }
        .side-brand {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 2px 4px 7px;
        }
        .side-orb {
            display: grid;
            place-items: center;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            color: #031018;
            font-size: 13px;
            font-weight: 800;
            background: linear-gradient(145deg, var(--cian), var(--violeta));
            box-shadow: 0 0 24px rgba(84, 230, 255, .35);
        }
        .side-title { font-size: .78rem; font-weight: 750; letter-spacing: .03em; }
        .side-subtitle {
            color: var(--cian);
            font-size: .54rem;
            letter-spacing: .14em;
            margin-top: 1px;
        }
        .side-section {
            margin: 1px 0 0;
            color: var(--texto-suave);
            font-size: .55rem;
            font-weight: 750;
            letter-spacing: .13em;
            text-transform: uppercase;
        }
        .st-key-sidebar_contexto [data-testid="stVerticalBlock"],
        .st-key-sidebar_archivos [data-testid="stVerticalBlock"] {
            gap: .35rem;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] {
            border-color: rgba(91, 224, 255, .14);
            background: rgba(7, 14, 30, .45);
        }
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
            min-height: 82px;
            padding: .65rem;
            background: rgba(4, 9, 21, .72);
        }
        .command-header {
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: 52px;
            padding: 7px 14px;
            border: 1px solid var(--borde);
            border-radius: 14px;
            background: linear-gradient(110deg, rgba(12, 23, 49, .94), rgba(21, 16, 53, .86));
            box-shadow: 0 12px 38px rgba(0, 0, 0, .22), inset 0 0 35px rgba(84, 230, 255, .025);
        }
        .command-header::after {
            content: "";
            position: absolute;
            inset: auto -6% -28px 38%;
            height: 44px;
            background: linear-gradient(90deg, transparent, rgba(84, 230, 255, .19), transparent);
            transform: skewX(-24deg);
        }
        .command-eyebrow {
            color: var(--cian);
            font-size: .67rem;
            letter-spacing: .18em;
            text-transform: uppercase;
        }
        .command-title {
            margin-top: 2px;
            font-size: 1.02rem;
            font-weight: 760;
            letter-spacing: .02em;
        }
        .online-badge {
            display: flex;
            align-items: center;
            gap: 7px;
            color: var(--verde);
            font-size: .68rem;
            font-weight: 700;
            letter-spacing: .13em;
            z-index: 1;
        }
        .online-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--verde);
            box-shadow: 0 0 13px var(--verde);
        }
        .diagnostic-strip {
            display: grid;
            grid-template-columns: 1fr 1.1fr 1.3fr .65fr .75fr;
            gap: 1px;
            overflow: hidden;
            margin: 4px 0;
            border: 1px solid rgba(139, 124, 255, .2);
            border-radius: 9px;
            background: rgba(139, 124, 255, .18);
        }
        .diagnostic-item {
            min-width: 0;
            padding: 3px 7px;
            background: rgba(7, 14, 31, .94);
        }
        .diagnostic-label {
            color: var(--texto-suave);
            font-size: .48rem;
            letter-spacing: .1em;
            text-transform: uppercase;
        }
        .diagnostic-value {
            overflow: hidden;
            margin-top: 0;
            color: var(--texto);
            font-size: .64rem;
            font-weight: 650;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .st-key-chat_area {
            border: 1px solid var(--borde) !important;
            border-radius: 10px !important;
            background:
                linear-gradient(rgba(6, 12, 27, .88), rgba(6, 12, 27, .88)),
                linear-gradient(135deg, rgba(84, 230, 255, .08), rgba(155, 124, 255, .08));
            box-shadow: inset 0 0 45px rgba(32, 87, 128, .05);
        }
        [data-testid="stChatMessage"] {
            width: 95%;
            margin-right: auto;
            background: rgba(14, 24, 48, .76);
            border: 1px solid rgba(125, 164, 218, .14);
            border-radius: 8px;
            padding: .1rem .15rem;
            margin-bottom: .3rem;
            font-size: .85rem;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user\"]) {
            width: 90%;
            margin-right: 0;
            margin-left: auto;
            border-color: rgba(155, 124, 255, .28);
            background: rgba(38, 26, 76, .66);
        }
        [data-testid="stChatInput"] {
            border-color: rgba(84, 230, 255, .3);
            background: rgba(9, 17, 35, .97);
            box-shadow: 0 0 24px rgba(84, 230, 255, .07);
        }
        .documento {
            border: 1px solid rgba(108, 153, 213, .16);
            border-radius: 8px;
            padding: 4px 6px;
            margin-bottom: 4px;
            background: rgba(9, 17, 36, .72);
        }
        .documento-nombre { color: var(--texto); font-size: .68rem; font-weight: 650; }
        .documento-detalle { color: var(--texto-suave); font-size: .58rem; margin-top: 1px; }
        .fuente-rag {
            border-left: 2px solid var(--cian);
            padding: 3px 5px;
            margin: 3px 0;
            border-radius: 0 6px 6px 0;
            background: rgba(26, 76, 103, .22);
            color: #cdefff;
            font-size: .64rem;
        }
        .st-key-panel_fuentes {
            border: 1px solid rgba(84, 230, 255, .2) !important;
            border-radius: 10px !important;
            background: rgba(7, 15, 31, .92);
        }
        .panel-fuentes-titulo {
            color: var(--cian);
            font-size: .54rem;
            font-weight: 750;
            letter-spacing: .13em;
            text-transform: uppercase;
        }
        .panel-fuentes-ayuda {
            margin: 2px 0 5px;
            color: var(--texto-suave);
            font-size: .58rem;
        }
        [data-testid="stButton"] button {
            border-color: rgba(117, 151, 214, .25);
            background: rgba(12, 21, 43, .82);
        }
        [data-testid="stButton"] button:hover {
            border-color: var(--cian);
            color: var(--cian);
        }
        .st-key-preguntas_sugeridas {
            width: 100%;
            margin: 0;
            padding: 0;
        }
        .st-key-preguntas_sugeridas > div {
            gap: .15rem;
        }
        .st-key-preguntas_sugeridas [data-testid="stButton"] button {
            min-height: 1.2rem;
            background: rgba(12, 21, 43, .2);
            font-size: .55rem;
            padding: .15rem .25rem;
            border: 1px solid rgba(84, 230, 255, .05);
            margin: 0;
            line-height: 1.1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        [data-testid="stSidebar"] hr { border-color: rgba(91, 224, 255, .12); }
        @media (max-width: 900px) {
            .diagnostic-strip { grid-template-columns: repeat(2, 1fr); }
            [data-testid="stSidebar"] {
                width: 250px !important;
                min-width: 250px !important;
                max-width: 250px !important;
            }
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
    st.session_state.setdefault("pregunta_pendiente", None)
    st.session_state.setdefault("mostrar_fuentes", True)
    st.session_state.setdefault("prueba_modelo", None)
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
        st.session_state.pregunta_pendiente = None
        st.session_state.mostrar_fuentes = True
        st.session_state.diagnostico = {"fragmentos": 0, "tiempo": None}


def _mostrar_documentos(empresa: str, visibilidad: str) -> None:
    documentos = listar_documentos(empresa, visibilidad)
    if not documentos:
        st.caption("Todavía no hay documentos en esta carpeta.")
        return
    for documento in documentos:
        col_doc, col_delete = st.columns([4, 1])
        with col_doc:
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
        with col_delete:
            if st.button(
                "🗑️",
                key=f"delete_{documento.nombre}_{visibilidad}",
                help=f"Eliminar {documento.nombre}",
                use_container_width=True,
            ):
                try:
                    eliminar_documento(documento.nombre, empresa, visibilidad)
                    st.toast(f"{documento.nombre} eliminado.", icon="✅")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))


def _panel_lateral(
    empresas: list[str],
    empresa_activa: str,
) -> tuple[str, str]:
    with st.sidebar:
        st.markdown(
            """
            <div class="side-brand">
                <div class="side-orb">A</div>
                <div>
                    <div class="side-title">KNOWLEDGE CORE</div>
                    <div class="side-subtitle">BOT 2050 // ONLINE</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        tab_general, tab_public, tab_private = st.tabs(["⚙️ General", "🌐 Public", "🔒 Private"])
        
        # Variables para almacenar estado
        guardar = False
        procesar = False
        archivos = None
        visibilidad_procesar = None
        
        with tab_general:
            st.markdown(
                '<div class="side-section">Contexto del chat</div>',
                unsafe_allow_html=True,
            )
            empresa = st.selectbox(
                "Empresa",
                empresas,
                index=(
                    empresas.index(empresa_activa)
                    if empresa_activa in empresas
                    else 0
                ),
            )
            perfil = st.selectbox(
                "Acceso del agente",
                ("public", "internal"),
                format_func=ETIQUETAS_PERFIL.get,
                help="Internal consulta documentos Public y Private.",
            )
            
            st.markdown(
                '<div class="side-section">Configuración LLM</div>',
                unsafe_allow_html=True,
            )
            
            # Obtener valor actual de LLM_MODEL del .env
            from dotenv import dotenv_values
            ruta_env = RAIZ_AGENTE / ".env"
            valores_env = dotenv_values(ruta_env) if ruta_env.exists() else {}
            llm_model_actual = valores_env.get("LLM_MODEL", "gemini-2.5-flash")
            
            col_input, col_guardar = st.columns([4, 1])
            with col_input:
                llm_model_nuevo = st.text_input(
                    "LLM_MODEL",
                    value=llm_model_actual,
                    help="Modelo de lenguaje a utilizar (ej: gemini-2.5-flash, gemini-2.5-pro)",
                    label_visibility="visible",
                )
            with col_guardar:
                if st.button(
                    "💾",
                    help="Guarda el modelo en el archivo .env",
                    key="guardar_llm_model",
                ):
                    try:
                        actualizar_valor_env(ruta_env, "LLM_MODEL", llm_model_nuevo)
                        st.toast("Modelo actualizado en .env", icon="✅")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Error al guardar: {error}")
            
            if st.button(
                "Probar Modelo",
                use_container_width=True,
                help="Comprueba Gemini sin consultar documentos ni índices.",
            ):
                with st.spinner("Enviando prueba mínima a Gemini..."):
                    st.session_state.prueba_modelo = probar_modelo()

            resultado_prueba = st.session_state.prueba_modelo
            if resultado_prueba is not None:
                if resultado_prueba.exito:
                    st.success(f"Respuesta de {resultado_prueba.modelo}")
                else:
                    referencia = " · ".join(
                        valor
                        for valor in (
                            (
                                f"HTTP {resultado_prueba.codigo}"
                                if resultado_prueba.codigo
                                else ""
                            ),
                            resultado_prueba.estado or "",
                        )
                        if valor
                    )
                    st.error(
                        f"Fallo de {resultado_prueba.modelo}"
                        + (f" · {referencia}" if referencia else "")
                    )
                st.code(resultado_prueba.respuesta, language="text")
                st.caption("Prueba directa: no utiliza RAG, documentos ni embeddings.")
        
        with tab_public:
            visibilidad = "Public"
            st.markdown(
                '<div class="side-section">Documentos Public</div>',
                unsafe_allow_html=True,
            )
            st.caption("Documentación versionable y apta para demostraciones.")
            
            with st.expander("＋ Agregar documentos a Public"):
                formatos = ", ".join(
                    f".{extension}" for extension in EXTENSIONES_SOPORTADAS
                )
                st.caption(f"Formatos disponibles: {formatos}.")
                archivos_public = st.file_uploader(
                    "Seleccionar documentos",
                    type=list(EXTENSIONES_CARGADOR),
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                    key="uploader_public",
                    help=(
                        "Los PDF deben contener texto seleccionable. "
                        "Para archivos .doc, convierte primero a .docx."
                    ),
                )
                if st.button(
                    "Guardar en Public",
                    type="primary",
                    use_container_width=True,
                    disabled=not archivos_public,
                    key="guardar_public",
                ):
                    guardar = True
                    archivos = archivos_public
                    visibilidad_procesar = visibilidad
            
            if st.button(
                "↻ Sincronizar conocimiento Public",
                use_container_width=True,
                help="Actualiza el índice RAG con los documentos Public guardados.",
                key="procesar_public",
            ):
                procesar = True
                visibilidad_procesar = visibilidad
            
            cantidad_documentos = len(listar_documentos(empresa, visibilidad))
            with st.expander(
                f"Documentos en Public · {cantidad_documentos}",
                expanded=True,
            ):
                _mostrar_documentos(empresa, visibilidad)
        
        with tab_private:
            visibilidad = "Private"
            st.markdown(
                '<div class="side-section">Documentos Private</div>',
                unsafe_allow_html=True,
            )
            st.caption("Documentación local protegida y no versionada.")
            
            with st.expander("＋ Agregar documentos a Private"):
                formatos = ", ".join(
                    f".{extension}" for extension in EXTENSIONES_SOPORTADAS
                )
                st.caption(f"Formatos disponibles: {formatos}.")
                archivos_private = st.file_uploader(
                    "Seleccionar documentos",
                    type=list(EXTENSIONES_CARGADOR),
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                    key="uploader_private",
                    help=(
                        "Los PDF deben contener texto seleccionable. "
                        "Para archivos .doc, convierte primero a .docx."
                    ),
                )
                if st.button(
                    "Guardar en Private",
                    type="primary",
                    use_container_width=True,
                    disabled=not archivos_private,
                    key="guardar_private",
                ):
                    guardar = True
                    archivos = archivos_private
                    visibilidad_procesar = visibilidad
            
            if st.button(
                "↻ Sincronizar conocimiento Private",
                use_container_width=True,
                help="Actualiza el índice RAG con los documentos Private guardados.",
                key="procesar_private",
            ):
                procesar = True
                visibilidad_procesar = visibilidad
            
            cantidad_documentos = len(listar_documentos(empresa, visibilidad))
            with st.expander(
                f"Documentos en Private · {cantidad_documentos}",
                expanded=True,
            ):
                _mostrar_documentos(empresa, visibilidad)

        if guardar and archivos and visibilidad_procesar:
            try:
                guardados = guardar_documentos(archivos, empresa, visibilidad_procesar)
                st.toast(
                    f"{len(guardados)} documento(s) guardado(s).",
                    icon="✅",
                )
                st.rerun()
            except ValueError as error:
                st.error(str(error))

        if procesar and visibilidad_procesar:
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
                        visibilidad_procesar,
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
        
        return empresa, perfil


def _mostrar_diagnostico(
    empresa: str,
    perfil: str,
    modelo: str,
    fragmentos: int,
    tiempo: float | None,
) -> None:
    tiempo_texto = f"{tiempo:.2f} s" if tiempo is not None else "—"
    valores = (
        ("Empresa", empresa),
        ("Perfil", ETIQUETAS_PERFIL[perfil]),
        ("Modelo", modelo),
        ("Fragmentos", str(fragmentos)),
        ("Tiempo total", tiempo_texto),
    )
    elementos = "".join(
        (
            '<div class="diagnostic-item">'
            f'<div class="diagnostic-label">{escape(etiqueta)}</div>'
            f'<div class="diagnostic-value" title="{escape(valor)}">'
            f"{escape(valor)}</div></div>"
        )
        for etiqueta, valor in valores
    )
    st.markdown(
        f'<div class="diagnostic-strip">{elementos}</div>',
        unsafe_allow_html=True,
    )


def _mostrar_fuentes(fuentes: list[dict]) -> None:
    if not fuentes:
        return
    for fuente in fuentes:
        ubicacion = (
            f"Página: {fuente['pagina']}"
            if fuente.get("pagina") is not None
            else f"Sección: {escape(fuente['seccion'])}"
        )
        st.markdown(
            (
                '<div class="fuente-rag">'
                f"📄 <strong>{escape(fuente['archivo'])}</strong><br>"
                f"{ubicacion}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def _fuentes_respuesta_reciente() -> list[dict]:
    """Obtiene las fuentes de la última respuesta, incluso si está vacía."""

    for mensaje in reversed(st.session_state.mensajes):
        if mensaje["rol"] == "assistant":
            return mensaje.get("fuentes", [])
    return []


def _panel_fuentes() -> None:
    """Muestra una sola vez los documentos usados por la respuesta reciente."""

    fuentes = _fuentes_respuesta_reciente()
    # Una sección puede llegar desde varios fragmentos; se presenta una sola vez.
    fuentes_unicas = list(
        {
            (fuente["archivo"], fuente["seccion"], fuente.get("pagina")): fuente
            for fuente in fuentes
        }.values()
    )

    with st.container(height=180, border=True, key="panel_fuentes"):
        st.markdown(
            (
                '<div class="panel-fuentes-titulo">Documentos consultados</div>'
                '<div class="panel-fuentes-ayuda">Fuentes de la última respuesta</div>'
            ),
            unsafe_allow_html=True,
        )
        if fuentes_unicas:
            _mostrar_fuentes(fuentes_unicas)
        else:
            st.caption("Las fuentes aparecerán aquí después de una respuesta.")


def _procesar_pregunta_pendiente(empresa: str, perfil: str) -> None:
    """Resuelve la pregunta después de que su burbuja ya fue mostrada."""

    pregunta = st.session_state.pregunta_pendiente
    if not pregunta:
        return

    try:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Consultando los documentos..."):
                resultado = _obtener_servicio(empresa).consultar(
                    pregunta,
                    perfil,
                    top_k=5,
                )

            texto = _texto_sin_bloque_fuentes(resultado.respuesta.texto)
            fuentes = [asdict(fuente) for fuente in resultado.respuesta.fuentes]
            st.markdown(texto)

        st.session_state.mensajes.append(
            {
                "id": str(uuid4()),
                "rol": "assistant",
                "texto": texto,
                "fuentes": fuentes,
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
    finally:
        st.session_state.pregunta_pendiente = None

    st.rerun()


def _mostrar_chat(empresa: str, perfil: str) -> None:
    # El historial se desplaza dentro de este panel para mantener siempre visible
    # el encabezado, los accesos rápidos y la caja de entrada de la aplicación.
    with st.container(height=280, border=True, key="chat_area"):
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
                    valor = st.feedback(
                        "thumbs",
                        key=f"feedback_{mensaje['id']}",
                    )
                    if valor is not None:
                        st.session_state.feedback[mensaje["id"]] = valor

        # Esta ejecución ocurre después del rerun que dibujó la pregunta. Así el
        # usuario ve su mensaje y el estado de consulta mientras responde el RAG.
        _procesar_pregunta_pendiente(empresa, perfil)


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

    empresa, perfil = _panel_lateral(empresas, empresa_activa)

    _sincronizar_contexto(empresa, perfil)
    modelo = cargar_configuracion_llm().modelo
    diagnostico = st.session_state.diagnostico

    _mostrar_diagnostico(
        empresa,
        perfil,
        modelo,
        diagnostico["fragmentos"],
        diagnostico["tiempo"],
    )

    control_chat, control_fuentes = st.columns(
        (4, 1),
        vertical_alignment="center",
    )
    with control_chat:
        st.caption("CONVERSACIÓN DOCUMENTAL")
    with control_fuentes:
        st.toggle("Mostrar fuentes", key="mostrar_fuentes")

    if st.session_state.mostrar_fuentes:
        columna_chat, columna_fuentes = st.columns((3.5, 1), gap="small")
        with columna_chat:
            _mostrar_chat(empresa, perfil)
        with columna_fuentes:
            _panel_fuentes()
    else:
        _mostrar_chat(empresa, perfil)

    pregunta_sugerida = None
    with st.container(key="preguntas_sugeridas"):
        cols = st.columns(3)
        for col, sugerencia in zip(cols, PREGUNTAS_SUGERIDAS):
            if col.button(sugerencia, key=f"sug_{sugerencia}", use_container_width=True):
                pregunta_sugerida = sugerencia

    # Dentro de un contenedor, el input queda integrado en el flujo de la página
    # y no reserva un bloque vacío para fijarse al borde inferior de la ventana.
    with st.container(key="entrada_chat"):
        pregunta_escrita = st.chat_input("Escribe tu pregunta aquí...")
    pregunta = pregunta_sugerida or pregunta_escrita
    if pregunta:
        st.session_state.mensajes.append(
            {"id": str(uuid4()), "rol": "user", "texto": pregunta}
        )
        st.session_state.pregunta_pendiente = pregunta
        # Primer rerun: muestra la pregunta antes de comenzar la consulta lenta.
        st.rerun()


if __name__ == "__main__":
    main()
