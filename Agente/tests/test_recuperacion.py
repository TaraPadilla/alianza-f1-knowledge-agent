"""Pruebas de recuperación con embeddings simulados y sin usar Gemini."""

import tempfile
import unittest
from pathlib import Path

import chromadb

from Agente.app.procesamiento.embeddings import ConfiguracionEmbeddings
from Agente.app.procesamiento.indice_vectorial import reconstruir_indice
from Agente.app.procesamiento.modelos import FragmentoMarkdown
from Agente.app.recuperacion import (
    ErrorRecuperacion,
    FiltrosRecuperacion,
    recuperar_fragmentos,
)


class EmbeddingsTematicos:
    """Ubica tres temas en ejes distintos para obtener resultados predecibles."""

    def __init__(self, fallar_consulta: bool = False) -> None:
        self.fallar_consulta = fallar_consulta
        self.consultas: list[str] = []

    @staticmethod
    def _vector(texto: str) -> list[float]:
        normalizado = texto.casefold()
        if "vacaciones" in normalizado or "licencia remunerada" in normalizado:
            return [1.0, 0.0, 0.0]
        if "ventas" in normalizado or "producto" in normalizado:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(texto) for texto in texts]

    def embed_query(self, text: str) -> list[float]:
        self.consultas.append(text)
        if self.fallar_consulta:
            raise RuntimeError("Fallo simulado en la consulta")
        return self._vector(text)


class RecuperacionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temporal.name)
        self.configuracion = ConfiguracionEmbeddings(
            modelo="simulado",
            dimensiones=3,
            directorio_vectorial=self.raiz / ".vectorstore",
            clave_api="no-utilizada",
        )
        self.proveedor = EmbeddingsTematicos()

    def tearDown(self) -> None:
        chromadb.api.client.SharedSystemClient.clear_system_cache()
        self.temporal.cleanup()

    @staticmethod
    def _fragmento(
        numero: int,
        contenido: str,
        *,
        visibilidad: str = "Public",
        empresa: str = "EmpresaPrueba",
        archivo: str = "manual.md",
        seccion: str = "Política",
    ) -> FragmentoMarkdown:
        ruta = f"{empresa}/{visibilidad}/{archivo}"
        return FragmentoMarkdown(
            contenido_markdown=f"# {seccion}\n\n{contenido}",
            empresa=empresa,
            visibilidad=visibilidad,
            ruta_relativa=ruta,
            titulo_seccion=seccion,
            nivel_seccion=1,
            indice_seccion=numero,
            indice_fragmento_seccion=1,
            total_fragmentos_seccion=1,
            indice_fragmento_documento=numero,
            referencia_fragmento=f"{ruta}#seccion-{numero}-fragmento-1",
        )

    def _crear_indice(
        self,
        fragmentos: list[FragmentoMarkdown],
        perfil: str = "public",
    ) -> None:
        reconstruir_indice(
            fragmentos,
            perfil=perfil,
            configuracion=self.configuracion,
            proveedor=self.proveedor,
            empresa="EmpresaPrueba",
        )

    def test_recupera_primero_el_fragmento_semanticamente_mas_cercano(self) -> None:
        vacaciones = self._fragmento(1, "La licencia remunerada cubre vacaciones.")
        ventas = self._fragmento(2, "Las ventas del producto aumentaron.")
        self._crear_indice([vacaciones, ventas])

        resultados = recuperar_fragmentos(
            "¿Cuántos días de vacaciones tengo?",
            "public",
            self.configuracion,
            self.proveedor,
            empresa="EmpresaPrueba",
            top_k=2,
        )

        self.assertEqual(resultados[0].referencia_fragmento, vacaciones.referencia_fragmento)
        self.assertLessEqual(resultados[0].distancia, resultados[1].distancia)
        self.assertEqual(self.proveedor.consultas, ["¿Cuántos días de vacaciones tengo?"])

    def test_top_k_limita_los_resultados(self) -> None:
        fragmentos = [
            self._fragmento(numero, f"Información de ventas del producto {numero}")
            for numero in range(1, 4)
        ]
        self._crear_indice(fragmentos)

        resultados = recuperar_fragmentos(
            "ventas",
            "public",
            self.configuracion,
            self.proveedor,
            empresa="EmpresaPrueba",
            top_k=2,
        )

        self.assertEqual(len(resultados), 2)

    def test_conserva_contenido_distancia_y_todos_los_metadatos(self) -> None:
        fragmento = self._fragmento(
            3,
            "Contenido sobre ventas.",
            archivo="comercial.md",
            seccion="Resultados",
        )
        self._crear_indice([fragmento])

        resultado = recuperar_fragmentos(
            "ventas",
            "public",
            self.configuracion,
            self.proveedor,
            empresa="EmpresaPrueba",
        )[0]

        self.assertEqual(resultado.contenido_markdown, fragmento.contenido_markdown)
        self.assertIsInstance(resultado.distancia, float)
        for clave, valor in fragmento.metadatos().items():
            self.assertEqual(getattr(resultado, clave), valor)

    def test_aplica_filtros_combinados_en_chroma(self) -> None:
        esperado = self._fragmento(
            1,
            "Ventas internas.",
            archivo="interno.md",
            seccion="Ventas",
        )
        otro = self._fragmento(
            2,
            "Ventas generales.",
            archivo="general.md",
            seccion="Resumen",
        )
        self._crear_indice([esperado, otro])

        resultados = recuperar_fragmentos(
            "ventas",
            "public",
            self.configuracion,
            self.proveedor,
            empresa="EmpresaPrueba",
            filtros=FiltrosRecuperacion(
                visibilidad="Public",
                ruta_relativa=esperado.ruta_relativa,
                titulo_seccion="Ventas",
            ),
        )

        self.assertEqual(
            [resultado.referencia_fragmento for resultado in resultados],
            [esperado.referencia_fragmento],
        )

    def test_perfil_internal_puede_filtrar_private(self) -> None:
        publico = self._fragmento(1, "Ventas públicas.")
        privado = self._fragmento(
            2,
            "Ventas privadas.",
            visibilidad="Private",
            archivo="privado.md",
        )
        self._crear_indice([publico, privado], perfil="internal")

        resultados = recuperar_fragmentos(
            "ventas",
            "internal",
            self.configuracion,
            self.proveedor,
            empresa="EmpresaPrueba",
            filtros=FiltrosRecuperacion(visibilidad="Private"),
        )

        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].visibilidad, "Private")

    def test_perfil_public_rechaza_filtro_private(self) -> None:
        with self.assertRaisesRegex(ErrorRecuperacion, "no permite"):
            recuperar_fragmentos(
                "ventas",
                "public",
                self.configuracion,
                self.proveedor,
                empresa="EmpresaPrueba",
                filtros=FiltrosRecuperacion(visibilidad="Private"),
            )

    def test_coleccion_vacia_devuelve_lista_sin_generar_embedding(self) -> None:
        self._crear_indice([])

        resultados = recuperar_fragmentos(
            "ventas",
            "public",
            self.configuracion,
            self.proveedor,
            empresa="EmpresaPrueba",
        )

        self.assertEqual(resultados, [])
        self.assertEqual(self.proveedor.consultas, [])

    def test_indice_inexistente_produce_error_claro(self) -> None:
        with self.assertRaisesRegex(ErrorRecuperacion, "No existe el índice"):
            recuperar_fragmentos(
                "ventas",
                "public",
                self.configuracion,
                self.proveedor,
                empresa="EmpresaPrueba",
            )

    def test_propaga_el_fallo_del_proveedor(self) -> None:
        fragmento = self._fragmento(1, "Contenido de ventas.")
        self._crear_indice([fragmento])
        proveedor = EmbeddingsTematicos(fallar_consulta=True)

        with self.assertRaisesRegex(RuntimeError, "Fallo simulado"):
            recuperar_fragmentos(
                "ventas",
                "public",
                self.configuracion,
                proveedor,
                empresa="EmpresaPrueba",
            )

    def test_valida_pregunta_y_top_k(self) -> None:
        for pregunta, top_k, mensaje in (("  ", 5, "pregunta"), ("ventas", 0, "top_k")):
            with self.subTest(pregunta=pregunta, top_k=top_k):
                with self.assertRaisesRegex(ErrorRecuperacion, mensaje):
                    recuperar_fragmentos(
                        pregunta,
                        "public",
                        self.configuracion,
                        self.proveedor,
                        empresa="EmpresaPrueba",
                        top_k=top_k,
                    )


if __name__ == "__main__":
    unittest.main()
