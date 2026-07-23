"""Pruebas independientes para la configuración multiempresa."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agente.app.configuracion import (
    ErrorConfiguracion,
    actualizar_configuracion_operativa,
    cargar_configuracion,
    cargar_configuracion_operativa,
    confirmar_reindexacion_operativa,
    ruta_configuracion_operativa,
)


class ConfiguracionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temporal.name)
        self._crear_empresa("EmpresaPrueba")

    def tearDown(self) -> None:
        self.temporal.cleanup()

    def _crear_empresa(self, nombre: str) -> None:
        """Crea una estructura ficticia sin utilizar documentos empresariales."""

        (self.raiz / nombre / "Public").mkdir(parents=True)
        (self.raiz / nombre / "Private").mkdir()

    def test_parametro_directo_selecciona_empresa(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            configuracion = cargar_configuracion(
                empresa="EmpresaPrueba",
                raiz_agente=self.raiz,
            )

        self.assertEqual(configuracion.empresa, "EmpresaPrueba")
        self.assertEqual(configuracion.visibilidades, ("Public", "Private"))

    def test_parametro_directo_tiene_prioridad_sobre_entorno(self) -> None:
        self._crear_empresa("EmpresaEntorno")

        with patch.dict(
            os.environ,
            {"EMPRESA_ACTIVA": "EmpresaEntorno"},
            clear=True,
        ):
            configuracion = cargar_configuracion(
                empresa="EmpresaPrueba",
                raiz_agente=self.raiz,
            )

        self.assertEqual(configuracion.empresa, "EmpresaPrueba")

    def test_empresa_puede_provenir_del_entorno(self) -> None:
        with patch.dict(
            os.environ,
            {"EMPRESA_ACTIVA": "EmpresaPrueba"},
            clear=True,
        ):
            configuracion = cargar_configuracion(raiz_agente=self.raiz)

        self.assertEqual(configuracion.empresa, "EmpresaPrueba")

    def test_empresa_puede_provenir_del_archivo_env(self) -> None:
        archivo_env = self.raiz / ".env.prueba"
        archivo_env.write_text(
            "EMPRESA_ACTIVA=EmpresaPrueba\nVISIBILIDADES_PERMITIDAS=Public\n",
            encoding="utf-8",
        )

        with patch.dict(os.environ, {}, clear=True):
            configuracion = cargar_configuracion(
                raiz_agente=self.raiz,
                ruta_env=archivo_env,
            )

        self.assertEqual(configuracion.empresa, "EmpresaPrueba")
        self.assertEqual(configuracion.visibilidades, ("Public",))

    def test_falta_de_empresa_genera_error_claro(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                ErrorConfiguracion,
                "No se indicó una empresa",
            ):
                cargar_configuracion(
                    raiz_agente=self.raiz,
                    ruta_env=self.raiz / ".env-inexistente",
                )

    def test_rechaza_empresa_inexistente(self) -> None:
        with self.assertRaisesRegex(ErrorConfiguracion, "No existe la carpeta"):
            cargar_configuracion(
                empresa="EmpresaInexistente",
                raiz_agente=self.raiz,
            )

    def test_rechaza_ruta_como_nombre_de_empresa(self) -> None:
        with self.assertRaisesRegex(ErrorConfiguracion, "solo el nombre"):
            cargar_configuracion(
                empresa="../EmpresaPrueba",
                raiz_agente=self.raiz,
            )

    def test_permite_filtrar_solo_conocimiento_publico(self) -> None:
        configuracion = cargar_configuracion(
            empresa="EmpresaPrueba",
            visibilidades=["public"],
            raiz_agente=self.raiz,
        )

        self.assertEqual(configuracion.visibilidades, ("Public",))
        self.assertEqual(
            configuracion.rutas_conocimiento,
            (self.raiz.resolve() / "EmpresaPrueba" / "Public",),
        )

    def test_rechaza_visibilidad_desconocida(self) -> None:
        with self.assertRaisesRegex(ErrorConfiguracion, "Visibilidad desconocida"):
            cargar_configuracion(
                empresa="EmpresaPrueba",
                visibilidades=["Confidencial"],
                raiz_agente=self.raiz,
            )

    def test_inicializa_archivo_operativo_desde_env_actual(self) -> None:
        archivo_env = self.raiz / ".env.prueba"
        archivo_env.write_text(
            "EMPRESA_ACTIVA=EmpresaPrueba\n"
            "VISIBILIDADES_PERMITIDAS=Public\n"
            "LLM_MODEL=modelo-inicial\n"
            "EMBEDDING_MODEL=embedding-inicial\n"
            "EMBEDDING_DIMENSIONS=16\n",
            encoding="utf-8",
        )

        with patch.dict(os.environ, {}, clear=True):
            operativa = cargar_configuracion_operativa(
                raiz_agente=self.raiz,
                ruta_env=archivo_env,
            )

        self.assertEqual(operativa.empresa_activa, "EmpresaPrueba")
        self.assertEqual(operativa.visibilidades_permitidas, ("Public",))
        self.assertEqual(operativa.llm_model, "modelo-inicial")
        self.assertEqual(operativa.embedding_model, "embedding-inicial")
        self.assertEqual(operativa.embedding_dimensiones, 16)
        self.assertTrue(ruta_configuracion_operativa(self.raiz).is_file())

    def test_configuracion_persistente_tiene_prioridad_sobre_entorno(self) -> None:
        with patch.dict(
            os.environ,
            {
                "EMPRESA_ACTIVA": "EmpresaPrueba",
                "LLM_MODEL": "modelo-entorno-inicial",
            },
            clear=True,
        ):
            cargar_configuracion_operativa(raiz_agente=self.raiz)
            actualizar_configuracion_operativa(
                {"LLM_MODEL": "modelo-persistente"},
                raiz_agente=self.raiz,
            )

        with patch.dict(
            os.environ,
            {"LLM_MODEL": "modelo-entorno-nuevo"},
            clear=True,
        ):
            operativa = cargar_configuracion_operativa(
                raiz_agente=self.raiz
            )

        self.assertEqual(operativa.llm_model, "modelo-persistente")

    def test_cambio_llm_no_marca_reindexacion(self) -> None:
        operativa = actualizar_configuracion_operativa(
            {"LLM_MODEL": "modelo-nuevo"},
            raiz_agente=self.raiz,
        )

        self.assertEqual(operativa.llm_model, "modelo-nuevo")
        self.assertFalse(operativa.reindexacion_pendiente)

    def test_cambio_embeddings_marca_reindexacion(self) -> None:
        operativa = actualizar_configuracion_operativa(
            {
                "EMBEDDING_MODEL": "embedding-nuevo",
                "EMBEDDING_DIMENSIONS": 128,
            },
            raiz_agente=self.raiz,
        )

        self.assertTrue(operativa.reindexacion_pendiente)

        confirmada = confirmar_reindexacion_operativa(
            raiz_agente=self.raiz
        )
        self.assertFalse(confirmada.reindexacion_pendiente)

    def test_escritura_operativa_usa_reemplazo_atomico(self) -> None:
        with patch(
            "Agente.app.configuracion.os.replace",
            wraps=os.replace,
        ) as reemplazar:
            actualizar_configuracion_operativa(
                {"LLM_MODEL": "modelo-atomico"},
                raiz_agente=self.raiz,
            )

        self.assertGreaterEqual(reemplazar.call_count, 1)
        temporales = list((self.raiz / "config").glob("*.tmp"))
        self.assertEqual(temporales, [])


if __name__ == "__main__":
    unittest.main()
