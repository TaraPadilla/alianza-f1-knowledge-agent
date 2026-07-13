# Cursos - Alianza F1 Knowledge Agent

Esta carpeta contiene los ejercicios, notebooks y ejemplos desarrollados durante los cursos utilizados para el aprendizaje y construcción del proyecto **Alianza F1 Knowledge Agent**.

Su propósito es mantener separados los materiales de estudio del desarrollo del producto principal (`KnowledgeAgent`), permitiendo experimentar con nuevas tecnologías sin afectar el entorno del agente.

## Estructura

```
Cursos/
│
├── .venv/                  # Entorno virtual exclusivo para los cursos (no versionado)
├── requirements.txt        # Dependencias utilizadas por los notebooks
├── .env                    # Variables de entorno locales (no versionado)
│
├── Curso-01/
│   └── AgentsWithGradio.ipynb
│
├── Curso-02/
│   └── ...
│
└── README.md
```

## Entorno virtual

Los cursos utilizan un entorno virtual independiente ubicado en:

```
Cursos/.venv
```

Esto permite:

- mantener aisladas las dependencias de los cursos;
- evitar conflictos con el proyecto principal;
- reproducir fácilmente el entorno en otro equipo.

## Instalación

Desde la carpeta `Cursos` crear el entorno virtual (solo la primera vez):

```bash
python -m venv .venv
```

Activar el entorno.

### Windows

```powershell
.\.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Instalar las dependencias:

```bash
pip install -r requirements.txt
```

## Variables de entorno

Las claves de API no se almacenan dentro de los notebooks.

Crear un archivo `.env` con las credenciales necesarias.

Ejemplo:

```text
GOOGLE_API_KEY=xxxxxxxxxxxxxxxx
TAVILY_API_KEY=xxxxxxxxxxxxxxxx
```

Los notebooks cargan estas variables utilizando `python-dotenv`.

## Agregar nuevas dependencias

Cuando un nuevo curso requiera una librería adicional:

1. Agregar la dependencia al archivo `requirements.txt`.
2. Ejecutar:

```bash
pip install -r requirements.txt
```

No es necesario reinstalar todas las librerías manualmente; `pip` instalará únicamente las que falten.

## Notebooks

Cada curso mantiene sus propios notebooks dentro de una carpeta independiente.

Ejemplo:

```
Curso-01/
Curso-02/
Curso-03/
```

Todos los notebooks deben utilizar el entorno virtual ubicado en:

```
Cursos/.venv
```

## Relación con el proyecto

Esta carpeta tiene únicamente fines de aprendizaje y experimentación.

El desarrollo del producto empresarial se realiza de forma independiente dentro de la carpeta:

```
KnowledgeAgent/
```

De esta manera se mantiene una separación clara entre:

- material de estudio;
- pruebas;
- desarrollo del agente reutilizable para Alianza F1.