"""Pruebas de configuración y adaptación del LLM sin usar la red."""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Agente.app.generacion import (
    ConfiguracionLLM,
    ErrorConfiguracionLLM,
    ErrorLLM,
    GeminiLLM,
    cargar_configuracion_llm,
    probar_modelo,
)


class ModelosLLMSimulados:
    def __init__(self, respuesta) -> None:
        self.respuesta = respuesta
        self.solicitudes: list[dict] = []

    def generate_content(self, **solicitud):
        self.solicitudes.append(solicitud)
        return self.respuesta


class ClienteLLMSimulado:
    def __init__(self, respuesta) -> None:
        self.models = ModelosLLMSimulados(respuesta)


class ModelosLLMConError:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def generate_content(self, **solicitud):
        raise self.error


class ClienteLLMConError:
    def __init__(self, error: Exception) -> None:
        self.models = ModelosLLMConError(error)


class ProveedorLLMTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temporal.name)

    def tearDown(self) -> None:
        self.temporal.cleanup()

    def _archivo_env(self, contenido: str) -> Path:
        ruta = self.raiz / ".env.prueba"
        ruta.write_text(contenido, encoding="utf-8")
        return ruta

    def test_carga_modelo_y_oculta_clave(self) -> None:
        ruta_env = self._archivo_env(
            "GEMINI_API_KEY=clave-ficticia\nLLM_MODEL=modelo-prueba\n"
        )

        with patch.dict(os.environ, {}, clear=True):
            configuracion = cargar_configuracion_llm(
                raiz_agente=self.raiz,
                ruta_env=ruta_env,
            )

        self.assertEqual(configuracion.modelo, "modelo-prueba")
        self.assertNotIn("clave-ficticia", repr(configuracion))

    def test_entorno_tiene_prioridad_sobre_archivo(self) -> None:
        ruta_env = self._archivo_env(
            "GEMINI_API_KEY=archivo\nLLM_MODEL=modelo-archivo\n"
        )

        with patch.dict(os.environ, {"LLM_MODEL": "modelo-entorno"}, clear=True):
            configuracion = cargar_configuracion_llm(
                raiz_agente=self.raiz,
                ruta_env=ruta_env,
            )

        self.assertEqual(configuracion.modelo, "modelo-entorno")

    def test_rechaza_variables_faltantes(self) -> None:
        ruta_env = self._archivo_env("LLM_MODEL=modelo-prueba\n")

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ErrorConfiguracionLLM, "Faltan variables"):
                cargar_configuracion_llm(
                    raiz_agente=self.raiz,
                    ruta_env=ruta_env,
                )

    def test_adaptador_usa_modelo_sistema_y_esquema(self) -> None:
        respuesta = SimpleNamespace(
            parsed={
                "respuesta": "Respuesta respaldada",
                "informacion_encontrada": True,
                "fuentes_utilizadas": [1],
            },
            text=None,
        )
        cliente = ClienteLLMSimulado(respuesta)
        proveedor = GeminiLLM(
            ConfiguracionLLM("modelo-configurado", "no-utilizada"),
            cliente=cliente,
        )

        salida = proveedor.generar("Instrucción", "Pregunta y contexto")
        solicitud = cliente.models.solicitudes[0]

        self.assertEqual(solicitud["model"], "modelo-configurado")
        self.assertEqual(solicitud["contents"], "Pregunta y contexto")
        self.assertEqual(solicitud["config"].system_instruction, "Instrucción")
        self.assertEqual(solicitud["config"].response_mime_type, "application/json")
        self.assertEqual(salida.fuentes_utilizadas, (1,))

    def test_acepta_json_textual_si_parsed_no_esta_disponible(self) -> None:
        cliente = ClienteLLMSimulado(
            SimpleNamespace(
                parsed=None,
                text=(
                    '{"respuesta":"Respuesta","informacion_encontrada":true,'
                    '"fuentes_utilizadas":[1]}'
                ),
            )
        )
        proveedor = GeminiLLM(
            ConfiguracionLLM("modelo", "no-utilizada"),
            cliente=cliente,
        )

        salida = proveedor.generar("Sistema", "Usuario")

        self.assertTrue(salida.informacion_encontrada)

    def test_rechaza_estructura_invalida(self) -> None:
        cliente = ClienteLLMSimulado(
            SimpleNamespace(parsed={"respuesta": "Incompleta"}, text=None)
        )
        proveedor = GeminiLLM(
            ConfiguracionLLM("modelo", "no-utilizada"),
            cliente=cliente,
        )

        with self.assertRaisesRegex(ErrorLLM, "no indica"):
            proveedor.generar("Sistema", "Usuario")

    def test_clasifica_errores_api_sin_exponer_el_detalle_original(self) -> None:
        from google.genai.errors import APIError

        casos = (
            (401, "UNAUTHENTICATED", "API key"),
            (403, "PERMISSION_DENIED", "no tiene permiso"),
            (404, "NOT_FOUND", "modelo-prueba"),
            (429, "RESOURCE_EXHAUSTED", "cuota agotada"),
            (400, "INVALID_ARGUMENT", "no fue válida"),
            (503, "UNAVAILABLE", "fuera de servicio"),
            (504, "DEADLINE_EXCEEDED", "tiempo máximo"),
        )
        for codigo, estado, esperado in casos:
            with self.subTest(codigo=codigo):
                error_api = APIError(
                    codigo,
                    {
                        "error": {
                            "status": estado,
                            "message": "detalle-interno-no-debe-mostrarse",
                        }
                    },
                )
                proveedor = GeminiLLM(
                    ConfiguracionLLM("modelo-prueba", "no-utilizada"),
                    cliente=ClienteLLMConError(error_api),
                )

                with self.assertRaises(ErrorLLM) as contexto:
                    proveedor.generar("Sistema", "Usuario")

                mensaje = str(contexto.exception)
                self.assertIn(esperado, mensaje)
                self.assertIn(f"HTTP {codigo}", mensaje)
                self.assertNotIn("detalle-interno", mensaje)

    def test_prueba_modelo_devuelve_el_texto_sin_modificar(self) -> None:
        cliente = ClienteLLMSimulado(
            SimpleNamespace(parsed=None, text="\nMODELO_OK\n")
        )

        resultado = probar_modelo(
            ConfiguracionLLM("modelo-prueba", "no-utilizada"),
            cliente=cliente,
        )

        self.assertTrue(resultado.exito)
        self.assertEqual(resultado.respuesta, "\nMODELO_OK\n")
        solicitud = cliente.models.solicitudes[0]
        self.assertEqual(solicitud["model"], "modelo-prueba")
        self.assertNotIn("config", solicitud)
        self.assertNotIn("document", solicitud["contents"].casefold())

    def test_prueba_modelo_muestra_codigo_estado_y_mensaje_de_gemini(self) -> None:
        from google.genai.errors import APIError

        error = APIError(
            429,
            {
                "error": {
                    "status": "RESOURCE_EXHAUSTED",
                    "message": "Cuota de prueba agotada.",
                }
            },
        )

        resultado = probar_modelo(
            ConfiguracionLLM("modelo-prueba", "no-utilizada"),
            cliente=ClienteLLMConError(error),
        )

        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.codigo, 429)
        self.assertEqual(resultado.estado, "RESOURCE_EXHAUSTED")
        self.assertEqual(resultado.respuesta, "Cuota de prueba agotada.")


if __name__ == "__main__":
    unittest.main()
