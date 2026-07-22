"""Pruebas de extracción que usan exclusivamente contenido ficticio."""

import tempfile
import unittest
from pathlib import Path

from Agente.app.procesamiento import (
    DocumentoDescubierto,
    ErrorExtraccionDocumento,
    extraer_documento,
    extraer_documentos,
)
from Agente.app.procesamiento.extractores.markdown import extraer_markdown


class ExtractorMarkdownTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temporal.name)

    def tearDown(self) -> None:
        self.temporal.cleanup()

    def _documento(
        self,
        contenido: str,
        *,
        nombre: str = "manual.md",
        visibilidad: str = "Public",
        encoding: str = "utf-8",
    ) -> DocumentoDescubierto:
        ruta = self.raiz / nombre
        ruta.write_text(contenido, encoding=encoding, newline="")
        return DocumentoDescubierto(
            empresa="EmpresaPrueba",
            visibilidad=visibilidad,
            ruta_relativa=f"EmpresaPrueba/{visibilidad}/{nombre}",
            ruta_archivo=ruta,
        )

    def test_separa_documento_por_encabezados_y_niveles(self) -> None:
        documento = self._documento(
            "Introducción\n\n# Principal\nTexto\n\n## Detalle\nMás texto"
        )

        extraido = extraer_markdown(documento)

        self.assertEqual(len(extraido.secciones), 3)
        self.assertIsNone(extraido.secciones[0].titulo)
        self.assertEqual(extraido.secciones[0].nivel, 0)
        self.assertEqual(extraido.secciones[1].titulo, "Principal")
        self.assertEqual(extraido.secciones[1].nivel, 1)
        self.assertEqual(extraido.secciones[2].titulo, "Detalle")
        self.assertEqual(extraido.secciones[2].nivel, 2)

    def test_conserva_sintaxis_markdown(self) -> None:
        markdown = (
            "# Catálogo\n\n"
            "- **Servicio principal**\n"
            "- [Documentación](https://example.com)\n\n"
            "| Servicio | Estado |\n"
            "| --- | --- |\n"
            "| Consultoría | Activo |"
        )
        documento = self._documento(markdown)

        extraido = extraer_markdown(documento)

        self.assertEqual(extraido.contenido_markdown, markdown)

    def test_no_interpreta_encabezados_dentro_de_codigo(self) -> None:
        markdown = "# Ejemplo\n\n```python\n# Esto no es una sección\nprint('ok')\n```"
        documento = self._documento(markdown)

        extraido = extraer_markdown(documento)

        self.assertEqual(len(extraido.secciones), 1)
        self.assertIn("# Esto no es una sección", extraido.secciones[0].contenido_markdown)

    def test_normaliza_saltos_y_lineas_vacias_excesivas(self) -> None:
        documento = self._documento("# Título\r\n\r\n\r\n\r\nTexto\r\n")

        extraido = extraer_markdown(documento)

        self.assertEqual(extraido.contenido_markdown, "# Título\n\nTexto")

    def test_conserva_espacios_significativos_dentro_de_lineas(self) -> None:
        markdown = "# Tabla\n\n| Nombre   | Valor |\n|----------|-------|"
        documento = self._documento(markdown)

        extraido = extraer_markdown(documento)

        self.assertEqual(extraido.contenido_markdown, markdown)

    def test_acepta_utf8_con_bom(self) -> None:
        documento = self._documento(
            "# Información\nContenido en español",
            encoding="utf-8-sig",
        )

        extraido = extraer_markdown(documento)

        self.assertEqual(extraido.secciones[0].titulo, "Información")
        self.assertNotIn("\ufeff", extraido.contenido_markdown)

    def test_documento_sin_encabezados_es_una_sola_seccion(self) -> None:
        documento = self._documento("Un párrafo sin encabezado.")

        extraido = extraer_markdown(documento)

        self.assertEqual(len(extraido.secciones), 1)
        self.assertIsNone(extraido.secciones[0].titulo)
        self.assertEqual(extraido.secciones[0].contenido_markdown, "Un párrafo sin encabezado.")

    def test_documento_vacio_no_crea_secciones(self) -> None:
        documento = self._documento("")

        extraido = extraer_markdown(documento)

        self.assertEqual(extraido.secciones, ())
        self.assertEqual(extraido.contenido_markdown, "")

    def test_conserva_procedencia_y_orden_de_documentos(self) -> None:
        primero = self._documento("# Uno", nombre="uno.md")
        segundo = self._documento(
            "# Dos",
            nombre="dos.markdown",
            visibilidad="Private",
        )

        extraidos = extraer_documentos([primero, segundo])

        self.assertEqual(
            [documento.ruta_relativa for documento in extraidos],
            [primero.ruta_relativa, segundo.ruta_relativa],
        )
        self.assertEqual(extraidos[1].empresa, "EmpresaPrueba")
        self.assertEqual(extraidos[1].visibilidad, "Private")

    def test_rechaza_formato_no_registrado(self) -> None:
        documento = self._documento("datos", nombre="datos.csv")

        with self.assertRaisesRegex(ErrorExtraccionDocumento, "no soportado"):
            extraer_documento(documento)


if __name__ == "__main__":
    unittest.main()
