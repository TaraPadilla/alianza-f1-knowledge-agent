"""Pruebas de configuración sin llamadas reales a Gemini."""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Agente.app.procesamiento.embeddings import (
    ConfiguracionEmbeddings,
    ErrorConfiguracionEmbeddings,
    ErrorLimiteEmbeddings,
    GeminiEmbeddings,
    cargar_configuracion_embeddings,
)


class ModelosGeminiSimulados:
    """Registra solicitudes y devuelve vectores sin conectarse a Gemini."""

    def __init__(self) -> None:
        self.solicitudes = []

    def embed_content(self, **solicitud):
        self.solicitudes.append(solicitud)
        contenidos = solicitud["contents"]
        cantidad = len(contenidos) if isinstance(contenidos, list) else 1
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=[1.0, 2.0, 3.0])] * cantidad
        )


class ClienteGeminiSimulado:
    def __init__(self) -> None:
        self.models = ModelosGeminiSimulados()


class ModelosGeminiConLimite(ModelosGeminiSimulados):
    def __init__(self, fallos: int, espera: str = "0s") -> None:
        super().__init__()
        self.fallos = fallos
        self.espera = espera

    def embed_content(self, **solicitud):
        from google.genai.errors import ClientError

        self.solicitudes.append(solicitud)
        if len(self.solicitudes) <= self.fallos:
            raise ClientError(
                429,
                {
                    "error": {
                        "code": 429,
                        "message": "Límite simulado",
                        "status": "RESOURCE_EXHAUSTED",
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                                "retryDelay": self.espera,
                            }
                        ],
                    }
                },
            )
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=[1.0, 2.0, 3.0])]
        )


class ClienteGeminiConLimite:
    def __init__(self, fallos: int, espera: str = "0s") -> None:
        self.models = ModelosGeminiConLimite(fallos, espera)


class ConfiguracionEmbeddingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temporal.name)

    def tearDown(self) -> None:
        self.temporal.cleanup()

    def _archivo_env(self, contenido: str) -> Path:
        ruta = self.raiz / ".env.prueba"
        ruta.write_text(contenido, encoding="utf-8")
        return ruta

    def test_carga_nombres_existentes_del_env(self) -> None:
        ruta_env = self._archivo_env(
            "GEMINI_API_KEY=clave-ficticia\n"
            "EMBEDDING_MODEL=modelo-prueba\n"
            "EMBEDDING_DIMENSIONS=8\n"
            "VECTORSTORE_DIR=.vectorstore\n"
        )

        with patch.dict(os.environ, {}, clear=True):
            configuracion = cargar_configuracion_embeddings(
                raiz_agente=self.raiz,
                ruta_env=ruta_env,
            )

        self.assertEqual(configuracion.modelo, "modelo-prueba")
        self.assertEqual(configuracion.dimensiones, 8)
        self.assertEqual(
            configuracion.directorio_vectorial,
            self.raiz / ".vectorstore",
        )
        self.assertNotIn("clave-ficticia", repr(configuracion))

    def test_entorno_tiene_prioridad_sobre_archivo(self) -> None:
        ruta_env = self._archivo_env(
            "GEMINI_API_KEY=archivo\n"
            "EMBEDDING_MODEL=modelo-archivo\n"
            "EMBEDDING_DIMENSIONS=8\n"
            "VECTORSTORE_DIR=.vectorstore\n"
        )

        with patch.dict(
            os.environ,
            {"EMBEDDING_MODEL": "modelo-entorno"},
            clear=True,
        ):
            configuracion = cargar_configuracion_embeddings(
                raiz_agente=self.raiz,
                ruta_env=ruta_env,
            )

        self.assertEqual(configuracion.modelo, "modelo-entorno")

    def test_rechaza_variables_faltantes(self) -> None:
        ruta_env = self._archivo_env("EMBEDDING_MODEL=modelo-prueba\n")

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                ErrorConfiguracionEmbeddings,
                "Faltan variables",
            ):
                cargar_configuracion_embeddings(
                    raiz_agente=self.raiz,
                    ruta_env=ruta_env,
                )

    def test_rechaza_dimensiones_invalidas(self) -> None:
        ruta_env = self._archivo_env(
            "GEMINI_API_KEY=ficticia\n"
            "EMBEDDING_MODEL=modelo\n"
            "EMBEDDING_DIMENSIONS=no-es-numero\n"
            "VECTORSTORE_DIR=.vectorstore\n"
        )

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                ErrorConfiguracionEmbeddings,
                "debe ser un número entero",
            ):
                cargar_configuracion_embeddings(
                    raiz_agente=self.raiz,
                    ruta_env=ruta_env,
                )

    def test_rechaza_directorio_fuera_de_agente(self) -> None:
        ruta_env = self._archivo_env(
            "GEMINI_API_KEY=ficticia\n"
            "EMBEDDING_MODEL=modelo\n"
            "EMBEDDING_DIMENSIONS=8\n"
            "VECTORSTORE_DIR=../fuera\n"
        )

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                ErrorConfiguracionEmbeddings,
                "no puede salir",
            ):
                cargar_configuracion_embeddings(
                    raiz_agente=self.raiz,
                    ruta_env=ruta_env,
                )

    def test_adaptador_usa_modelo_y_dimensiones_configurados(self) -> None:
        cliente = ClienteGeminiSimulado()
        configuracion = ConfiguracionEmbeddings(
            modelo="modelo-configurado",
            dimensiones=3,
            directorio_vectorial=self.raiz / ".vectorstore",
            clave_api="no-utilizada",
        )
        proveedor = GeminiEmbeddings(configuracion, cliente=cliente)

        vectores = proveedor.embed_documents(["uno", "dos"])
        solicitud = cliente.models.solicitudes[0]

        self.assertEqual(len(vectores), 2)
        self.assertEqual(solicitud["model"], "modelo-configurado")
        self.assertEqual(solicitud["config"].output_dimensionality, 3)
        self.assertEqual(
            str(solicitud["config"].task_type),
            "RETRIEVAL_DOCUMENT",
        )

    def test_embedding_2_utiliza_instruccion_sin_task_type(self) -> None:
        cliente = ClienteGeminiSimulado()
        configuracion = ConfiguracionEmbeddings(
            modelo="gemini-embedding-2",
            dimensiones=3,
            directorio_vectorial=self.raiz / ".vectorstore",
            clave_api="no-utilizada",
        )
        proveedor = GeminiEmbeddings(configuracion, cliente=cliente)

        proveedor.embed_documents(["contenido"])
        solicitud = cliente.models.solicitudes[0]
        texto_enviado = solicitud["contents"][0].parts[0].text

        self.assertTrue(texto_enviado.startswith("title: none | text:"))
        self.assertIsNone(solicitud["config"].task_type)

    def test_limita_reintentos_429_a_dos(self) -> None:
        cliente = ClienteGeminiConLimite(fallos=3)
        esperas = []
        configuracion = ConfiguracionEmbeddings(
            modelo="modelo-prueba",
            dimensiones=3,
            directorio_vectorial=self.raiz / ".vectorstore",
            clave_api="no-utilizada",
        )
        proveedor = GeminiEmbeddings(
            configuracion,
            cliente=cliente,
            max_reintentos_429=2,
            espera_maxima=45,
            dormir=esperas.append,
        )

        with self.assertRaisesRegex(
            ErrorLimiteEmbeddings,
            "después de 2 reintentos",
        ):
            proveedor.embed_documents(["contenido"])

        self.assertEqual(len(cliente.models.solicitudes), 3)
        self.assertEqual(esperas, [0.0, 0.0])

    def test_finaliza_si_espera_supera_maximo(self) -> None:
        cliente = ClienteGeminiConLimite(fallos=1, espera="50s")
        esperas = []
        configuracion = ConfiguracionEmbeddings(
            modelo="modelo-prueba",
            dimensiones=3,
            directorio_vectorial=self.raiz / ".vectorstore",
            clave_api="no-utilizada",
        )
        proveedor = GeminiEmbeddings(
            configuracion,
            cliente=cliente,
            max_reintentos_429=2,
            espera_maxima=45,
            dormir=esperas.append,
        )

        with self.assertRaisesRegex(
            ErrorLimiteEmbeddings,
            "superando el máximo permitido",
        ):
            proveedor.embed_documents(["contenido"])

        self.assertEqual(len(cliente.models.solicitudes), 1)
        self.assertEqual(esperas, [])


if __name__ == "__main__":
    unittest.main()
