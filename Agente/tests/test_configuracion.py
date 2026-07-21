"""Pruebas independientes para la configuración multiempresa."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agente.app.configuracion import ErrorConfiguracion, cargar_configuracion


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


if __name__ == "__main__":
    unittest.main()
