"""Pruebas del descubrimiento de documentos, sin extraer su contenido."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agente.app.procesamiento import descubrir_conocimiento


class DescubrimientoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temporal.name)
        self._crear_empresa("EmpresaUno")
        self._crear_empresa("EmpresaDos")

        self._crear_archivo("EmpresaUno/Public/manual.md")
        self._crear_archivo("EmpresaUno/Public/guias/inicio.MARKDOWN")
        self._crear_archivo("EmpresaUno/Private/politicas.md")
        self._crear_archivo("EmpresaUno/Private/notas.txt")
        self._crear_archivo("EmpresaUno/Public/manual.docx")
        self._crear_archivo("EmpresaUno/Public/catalogo.PDF")
        self._crear_archivo("EmpresaUno/Private/datos.csv")
        self._crear_archivo("EmpresaUno/Public/legado.doc")
        self._crear_archivo("EmpresaUno/Public/.oculto.md")
        self._crear_archivo("EmpresaDos/Public/otro.md")

    def tearDown(self) -> None:
        self.temporal.cleanup()

    def _crear_empresa(self, nombre: str) -> None:
        (self.raiz / nombre / "Public").mkdir(parents=True)
        (self.raiz / nombre / "Private").mkdir()

    def _crear_archivo(self, ruta_relativa: str) -> None:
        ruta = self.raiz / ruta_relativa
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("contenido ficticio", encoding="utf-8")

    def test_descubre_public_y_private_en_una_coleccion(self) -> None:
        documentos = descubrir_conocimiento(
            empresa="EmpresaUno",
            raiz_agente=self.raiz,
        )

        self.assertEqual(len(documentos), 6)
        self.assertEqual(
            {documento.visibilidad for documento in documentos},
            {"Public", "Private"},
        )

    def test_filtra_solamente_public(self) -> None:
        documentos = descubrir_conocimiento(
            empresa="EmpresaUno",
            visibilidades=["Public"],
            raiz_agente=self.raiz,
        )

        self.assertEqual(len(documentos), 4)
        self.assertTrue(
            all(documento.visibilidad == "Public" for documento in documentos)
        )

    def test_filtra_solamente_private(self) -> None:
        documentos = descubrir_conocimiento(
            empresa="EmpresaUno",
            visibilidades="Private",
            raiz_agente=self.raiz,
        )

        self.assertEqual(len(documentos), 2)
        self.assertEqual(documentos[0].visibilidad, "Private")

    def test_conserva_empresa_visibilidad_y_ruta_relativa(self) -> None:
        documentos = descubrir_conocimiento(
            empresa="EmpresaUno",
            visibilidades="Private",
            raiz_agente=self.raiz,
        )
        documento = next(
            documento
            for documento in documentos
            if documento.ruta_relativa.endswith("politicas.md")
        )
        datos = documento.como_dict()

        self.assertEqual(
            datos,
            {
                "empresa": "EmpresaUno",
                "visibilidad": "Private",
                "ruta_relativa": "EmpresaUno/Private/politicas.md",
            },
        )
        self.assertNotIn(str(self.raiz), datos["ruta_relativa"])

    def test_ignora_formatos_no_registrados(self) -> None:
        documentos = descubrir_conocimiento(
            empresa="EmpresaUno",
            raiz_agente=self.raiz,
        )

        rutas = {documento.ruta_relativa for documento in documentos}
        self.assertNotIn("EmpresaUno/Private/datos.csv", rutas)
        self.assertNotIn("EmpresaUno/Public/legado.doc", rutas)

    def test_ignora_archivos_ocultos(self) -> None:
        documentos = descubrir_conocimiento(
            empresa="EmpresaUno",
            raiz_agente=self.raiz,
        )

        self.assertFalse(
            any(".oculto.md" in documento.ruta_relativa for documento in documentos)
        )

    def test_no_mezcla_documentos_de_otra_empresa(self) -> None:
        documentos = descubrir_conocimiento(
            empresa="EmpresaUno",
            raiz_agente=self.raiz,
        )

        self.assertTrue(
            all(documento.empresa == "EmpresaUno" for documento in documentos)
        )
        self.assertFalse(
            any("EmpresaDos" in documento.ruta_relativa for documento in documentos)
        )

    def test_utiliza_empresa_activa_del_entorno(self) -> None:
        with patch.dict(
            os.environ,
            {"EMPRESA_ACTIVA": "EmpresaDos"},
            clear=True,
        ):
            documentos = descubrir_conocimiento(raiz_agente=self.raiz)

        self.assertEqual(len(documentos), 1)
        self.assertEqual(documentos[0].empresa, "EmpresaDos")

    def test_devuelve_lista_vacia_si_no_hay_markdown(self) -> None:
        self._crear_empresa("EmpresaVacia")

        documentos = descubrir_conocimiento(
            empresa="EmpresaVacia",
            raiz_agente=self.raiz,
        )

        self.assertEqual(documentos, [])


if __name__ == "__main__":
    unittest.main()
