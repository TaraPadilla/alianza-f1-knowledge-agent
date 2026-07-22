FROM python:3.12-slim

# Configuración básica para una ejecución predecible dentro del contenedor.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

# Instalar primero las dependencias permite reutilizar la caché de Docker.
COPY Agente/requirements.txt /app/Agente/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/Agente/requirements.txt

# .dockerignore impide copiar documentos, índices, secretos y archivos locales.
COPY Agente /app/Agente

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"]

CMD ["streamlit", "run", "Agente/interfaz_streamlit.py"]
