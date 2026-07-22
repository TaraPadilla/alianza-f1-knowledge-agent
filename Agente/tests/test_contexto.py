"""Pruebas del ensamblaje de contexto sin invocar un LLM."""

import unittest

from Agente.app.recuperacion import FragmentoRecuperado, ensamblar_contexto


class ContextoTests(unittest.TestCase):
    @staticmethod
    def _resultado(numero: int, titulo: str | None = "Política") -> FragmentoRecuperado:
        return FragmentoRecuperado(
            contenido_markdown=f"## Contenido {numero}\n\n- Elemento Markdown",
            distancia=0.1 * numero,
            empresa="EmpresaPrueba",
            visibilidad="Public",
            ruta_relativa="EmpresaPrueba/Public/manual.md",
            titulo_seccion=titulo,
            nivel_seccion=2,
            indice_seccion=numero,
            indice_fragmento_seccion=1,
            total_fragmentos_seccion=1,
            indice_fragmento_documento=numero,
            referencia_fragmento=f"manual.md#fragmento-{numero}",
        )

    def test_conserva_markdown_y_referencias(self) -> None:
        contexto = ensamblar_contexto([self._resultado(1), self._resultado(2)])

        self.assertIn("## Contenido 1", contexto)
        self.assertIn("- Elemento Markdown", contexto)
        self.assertIn("[Fuente 1]", contexto)
        self.assertIn("[Fuente 2]", contexto)
        self.assertIn("Referencia: manual.md#fragmento-1", contexto)
        self.assertIn("\n\n---\n\n", contexto)

    def test_contexto_vacio_devuelve_cadena_vacia(self) -> None:
        self.assertEqual(ensamblar_contexto([]), "")

    def test_identifica_una_seccion_sin_encabezado(self) -> None:
        contexto = ensamblar_contexto([self._resultado(1, titulo=None)])

        self.assertIn("Sección: Sin encabezado", contexto)


if __name__ == "__main__":
    unittest.main()
