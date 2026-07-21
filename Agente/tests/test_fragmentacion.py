"""Pruebas del chunking Markdown con documentos ficticios."""

import unittest

from Agente.app.procesamiento import (
    DocumentoExtraido,
    SeccionMarkdown,
    fragmentar_documento,
    fragmentar_documentos,
)
from Agente.app.procesamiento.fragmentacion import ErrorFragmentacion


class FragmentacionTests(unittest.TestCase):
    def _documento(
        self,
        secciones: tuple[SeccionMarkdown, ...],
        *,
        nombre: str = "manual.md",
        visibilidad: str = "Public",
    ) -> DocumentoExtraido:
        return DocumentoExtraido(
            empresa="EmpresaPrueba",
            visibilidad=visibilidad,
            ruta_relativa=f"EmpresaPrueba/{visibilidad}/{nombre}",
            secciones=secciones,
        )

    def test_seccion_corta_permanece_completa(self) -> None:
        contenido = "# Resumen\n\n- Punto uno\n- Punto dos"
        documento = self._documento(
            (SeccionMarkdown("Resumen", 1, contenido),)
        )

        fragmentos = fragmentar_documento(
            documento,
            tamano_maximo=100,
            solapamiento=20,
        )

        self.assertEqual(len(fragmentos), 1)
        self.assertEqual(fragmentos[0].contenido_markdown, contenido)

    def test_no_combina_secciones_cortas(self) -> None:
        documento = self._documento(
            (
                SeccionMarkdown("Uno", 1, "# Uno\n\nTexto uno"),
                SeccionMarkdown("Dos", 1, "# Dos\n\nTexto dos"),
            )
        )

        fragmentos = fragmentar_documento(
            documento,
            tamano_maximo=100,
            solapamiento=20,
        )

        self.assertEqual(len(fragmentos), 2)
        self.assertEqual(fragmentos[0].titulo_seccion, "Uno")
        self.assertEqual(fragmentos[1].titulo_seccion, "Dos")

    def test_seccion_larga_respeta_tamano_maximo(self) -> None:
        cuerpo = " ".join(f"palabra{i}" for i in range(80))
        documento = self._documento(
            (SeccionMarkdown("Extensa", 2, f"## Extensa\n\n{cuerpo}"),)
        )

        fragmentos = fragmentar_documento(
            documento,
            tamano_maximo=120,
            solapamiento=20,
        )

        self.assertGreater(len(fragmentos), 1)
        self.assertTrue(
            all(len(fragmento.contenido_markdown) <= 120 for fragmento in fragmentos)
        )

    def test_repite_encabezado_una_sola_vez_por_fragmento(self) -> None:
        cuerpo = " ".join(f"dato{i}" for i in range(100))
        documento = self._documento(
            (SeccionMarkdown("Datos", 2, f"## Datos\n\n{cuerpo}"),)
        )

        fragmentos = fragmentar_documento(
            documento,
            tamano_maximo=100,
            solapamiento=20,
        )

        for fragmento in fragmentos:
            self.assertTrue(fragmento.contenido_markdown.startswith("## Datos\n\n"))
            self.assertEqual(fragmento.contenido_markdown.count("## Datos"), 1)

    def test_solapamiento_solo_reutiliza_el_cuerpo(self) -> None:
        cuerpo = " ".join(f"elemento{i:02d}" for i in range(70))
        documento = self._documento(
            (SeccionMarkdown("Lista", 1, f"# Lista\n\n{cuerpo}"),)
        )

        fragmentos = fragmentar_documento(
            documento,
            tamano_maximo=110,
            solapamiento=25,
        )
        cuerpos = [
            fragmento.contenido_markdown.removeprefix("# Lista\n\n")
            for fragmento in fragmentos
        ]

        for anterior, siguiente in zip(cuerpos, cuerpos[1:]):
            coincidencia = max(
                (
                    cantidad
                    for cantidad in range(1, min(25, len(anterior), len(siguiente)) + 1)
                    if anterior[-cantidad:] == siguiente[:cantidad]
                ),
                default=0,
            )
            self.assertGreater(coincidencia, 0)
            self.assertLessEqual(coincidencia, 25)

    def test_conserva_metadatos_y_referencia(self) -> None:
        documento = self._documento(
            (SeccionMarkdown("Interna", 3, "### Interna\n\nContenido"),),
            nombre="politicas.md",
            visibilidad="Private",
        )

        fragmento = fragmentar_documento(documento)[0]

        self.assertEqual(fragmento.empresa, "EmpresaPrueba")
        self.assertEqual(fragmento.visibilidad, "Private")
        self.assertEqual(fragmento.nivel_seccion, 3)
        self.assertEqual(fragmento.indice_seccion, 1)
        self.assertEqual(fragmento.indice_fragmento_seccion, 1)
        self.assertEqual(fragmento.total_fragmentos_seccion, 1)
        self.assertEqual(fragmento.indice_fragmento_documento, 1)
        self.assertEqual(
            fragmento.referencia_fragmento,
            "EmpresaPrueba/Private/politicas.md#seccion-1-fragmento-1",
        )
        self.assertNotIn("ruta_archivo", fragmento.metadatos())

    def test_numera_fragmentos_dentro_del_documento(self) -> None:
        documento = self._documento(
            (
                SeccionMarkdown("Uno", 1, "# Uno\n\nTexto"),
                SeccionMarkdown("Dos", 1, "# Dos\n\nTexto"),
            )
        )

        fragmentos = fragmentar_documento(documento)

        self.assertEqual(
            [fragmento.indice_fragmento_documento for fragmento in fragmentos],
            [1, 2],
        )

    def test_documento_vacio_no_genera_fragmentos(self) -> None:
        documento = self._documento(())

        self.assertEqual(fragmentar_documento(documento), [])

    def test_fragmenta_varios_documentos_en_orden(self) -> None:
        primero = self._documento(
            (SeccionMarkdown("Uno", 1, "# Uno"),),
            nombre="uno.md",
        )
        segundo = self._documento(
            (SeccionMarkdown("Dos", 1, "# Dos"),),
            nombre="dos.md",
        )

        fragmentos = fragmentar_documentos([primero, segundo])

        self.assertEqual(
            [fragmento.ruta_relativa for fragmento in fragmentos],
            [primero.ruta_relativa, segundo.ruta_relativa],
        )

    def test_valida_tamano_y_solapamiento(self) -> None:
        documento = self._documento(
            (SeccionMarkdown(None, 0, "Contenido"),)
        )

        casos = (
            {"tamano_maximo": 0, "solapamiento": 0},
            {"tamano_maximo": 100, "solapamiento": -1},
            {"tamano_maximo": 100, "solapamiento": 100},
        )
        for parametros in casos:
            with self.subTest(parametros=parametros):
                with self.assertRaises(ErrorFragmentacion):
                    fragmentar_documento(documento, **parametros)


if __name__ == "__main__":
    unittest.main()
