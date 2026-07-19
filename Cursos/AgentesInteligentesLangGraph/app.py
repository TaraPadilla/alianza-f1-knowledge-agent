# app.py
import gradio as gr
from new_backend import graph # Importa el grafo de tu nuevo backend
import uuid

# --- Función que será llamada por Gradio para ejecutar el agente ---
def generate_essay(topic: str, max_revisions: int):
    # Ejecuta el grafo del agente para generar una redacción y transmite las salidas en tiempo real.
    thread_id = str(uuid.uuid4())
    thread_config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "task": topic,
        "max_revisions": max_revisions,
        "revision_number": 0,
        "plan": "",
        "draft": "",
        "critique": "",
        "content": []
    }

    full_output = ""
    # Itera sobre el stream del grafo para obtener las salidas paso a paso
    for s in graph.stream(initial_state, thread_config):
        # La API de LangGraph devuelve un diccionario de diccionarios
        step_output = list(s.values())[0]

        # Formatea la salida para que sea más legible en la interfaz
        if "plan" in step_output:
            full_output += f"### �� Plan Generado:\n{step_output['plan']}\n\n"
        elif "content" in step_output:
            # Muestra el contenido de la investigación
            search_content = "\n".join(step_output['content'])
            full_output += f"### �� Contenido de Investigación:\n{search_content}\n\n"
        elif "draft" in step_output:
            full_output += f"### ✍️ Borrador Generado:\n{step_output['draft']}\n\n"
        elif "critique" in step_output:
            full_output += f"### �� Critica y Revisión:\n{step_output['critique']}\n\n"

        # Agrega una línea divisoria para separar los pasos
        full_output += "---\n" * 20 + "\n\n"
        
        yield full_output

# --- Interfaz de usuario con Gradio ---
# -- Creación de la Interfaz Gradio --
with gr.Blocks(theme=gr.themes.Default(spacing_size="sm", text_size="sm")) as demo:
    gr.Markdown("# �� Generador de Redacciones con Gemini y LangGraph")
    gr.Markdown(
        """
        Escribe el tema de tu redacción y el número de revisiones.
        El agente planificará, investigará, redactará y revisará el texto.
        """
    )
    with gr.Row():
        essay_topic = gr.Textbox(label="Tema de la Redacción", placeholder="Ej: La importancia de la inteligencia artificial en la educación")
        max_revisions_slider = gr.Slider(minimum=0, maximum=3, step=1, value=1, label="Número Máximo de Revisiones")
        generate_button = gr.Button("Generar Redacción", variant="primary")
    output_textbox = gr.Textbox(label="Proceso y Redacción Final", lines=20, max_lines=40)

    # Asocia el botón a la función Python
    generate_button.click(
        fn=generate_essay,
        inputs=[essay_topic, max_revisions_slider],
        outputs=output_textbox
    )

# Lanza la interfaz
if __name__ == "__main__":
    demo.launch(share=False)