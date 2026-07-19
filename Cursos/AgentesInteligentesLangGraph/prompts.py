prompt_instructions = {
    "triage_rules": {
        "ignore": "Newsletters de marketing, e-mails de spam, comunicados generales de la empresa",
        "notify": "Miembro del equipo convaleciente, notificaciones del sistema d build, Actualizaciones del status del proyecto",
        "respond": "Preguntas directas de miembros del equipo, solicitudes de reunión, informes de bugs críticos",
    },
    "agent_instructions": "Usa estas heerramientas cuando sea apropiado para ayudar a gestionar las tareas de Sarah de forma eficiente."
}

profile = {
    "name": "Sarah",
    "full_name": "Sarah Chen",
    "user_profile_background": "Ingeniera de software senior liderando un equipo de 5 desarrolladores",
}

email_respond = {
    "from": "Alice Smith <alice.smith@company.com>",
    "to": "Sarah Chen <sarah.chen@company.com>",
    "subject": "Duda rápida sobre la documentación de la API",
    "body": """
Hola Sarah,

Estaba revisando la documentación de la API para el nuevo servicio de autenticación y noté que algunos endpoints parecen faltar en las especificaciones. ¿Podrías ayudarme a aclarar si esto fue intencional o si debemos actualizar la documentación?

Específicamente, estoy buscando:
- /auth/refresh
- /auth/validate

¡Gracias!
Alice""",
}

triage_system_prompt = """
Eres un asistente de correo electrónico para {full_name}.

Información sobre la persona:
- Nombre: {name}
- Contexto profesional: {user_profile_background}

Tu tarea es analizar cada correo recibido y clasificarlo según estas reglas:

IGNORE:
{triage_no}

NOTIFY:
{triage_notify}

RESPOND:
{triage_email}

Criterios:
- Usa "ignore" cuando el correo sea irrelevante, promocional o no requiera atención.
- Usa "notify" cuando contenga información importante, pero no necesite una respuesta.
- Usa "respond" cuando el remitente haga una pregunta directa, solicite una acción,
  proponga una reunión o reporte un problema crítico.

Analiza el contenido completo del correo y devuelve la clasificación más adecuada.
"""

triage_user_prompt = """
Analiza el siguiente correo:

De: {author}
Para: {to}
Asunto: {subject}

Contenido:
{email_thread}
"""

agent_system_prompt = """
Hola {full_name}
Trabajas como {user_profile_background}
Instrucciones:
{instructions}
"""