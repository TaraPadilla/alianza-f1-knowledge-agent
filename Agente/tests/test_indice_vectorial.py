"""Pruebas de Chroma con embeddings simulados y contenido ficticio."""

import tempfile
import unittest
from pathlib import Path

import chromadb

from Agente.app.procesamiento.embeddings import ConfiguracionEmbeddings
from Agente.app.procesamiento.indice_vectorial import (
    ErrorIndiceVectorial,
    reconstruir_indice,
)
from Agente.app.procesamiento.modelos import FragmentoMarkdown


class EmbeddingsSimulados:
    """Vectores deterministas para probar sin red ni credenciales."""

    @staticmethod
    def _vector(texto: str) -> list[float]:
        return [
            float(len(texto)),
            float(sum(ord(caracter) for caracter in texto) % 997),
            float(texto.count(" ") + 1),
        ]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(texto) for texto in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class IndiceVectorialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temporal.name)
        self.configuracion = ConfiguracionEmbeddings(
            modelo="simulado",
            dimensiones=3,
            directorio_vectorial=self.raiz / ".vectorstore",
            clave_api="no-utilizada",
        )
        self.proveedor = EmbeddingsSimulados()

    def tearDown(self) -> None:
        chromadb.api.client.SharedSystemClient.clear_system_cache()
        self.temporal.cleanup()

    def _fragmento(
        self,
        numero: int,
        visibilidad: str = "Public",
        *,
        empresa: str = "EmpresaPrueba",
    ) -> FragmentoMarkdown:
        ruta = f"{empresa}/{visibilidad}/manual.md"
        return FragmentoMarkdown(
            contenido_markdown=f"# Sección\n\nContenido ficticio {numero}",
            empresa=empresa,
            visibilidad=visibilidad,
            ruta_relativa=ruta,
            titulo_seccion="Sección",
            nivel_seccion=1,
            indice_seccion=numero,
            indice_fragmento_seccion=1,
            total_fragmentos_seccion=1,
            indice_fragmento_documento=numero,
            referencia_fragmento=f"{ruta}#seccion-{numero}-fragmento-1",
        )

    def _leer_resultado(self, resultado):
        cliente = chromadb.PersistentClient(path=str(resultado.directorio))
        try:
            return cliente.get_collection(resultado.coleccion).get()
        finally:
            cliente.close()

    def test_persiste_contenido_y_todos_los_metadatos(self) -> None:
        fragmento = self._fragmento(1)

        resultado = reconstruir_indice(
            [fragmento],
            perfil="public",
            configuracion=self.configuracion,
            proveedor=self.proveedor,
        )
        datos = self._leer_resultado(resultado)

        self.assertEqual(datos["ids"], [fragmento.referencia_fragmento])
        self.assertEqual(datos["documents"], [fragmento.contenido_markdown])
        self.assertEqual(datos["metadatas"][0], fragmento.metadatos())

    def test_reconstruccion_no_genera_duplicados(self) -> None:
        fragmentos = [self._fragmento(1), self._fragmento(2)]

        for _ in range(2):
            resultado = reconstruir_indice(
                fragmentos,
                perfil="public",
                configuracion=self.configuracion,
                proveedor=self.proveedor,
            )

        datos = self._leer_resultado(resultado)
        self.assertEqual(len(datos["ids"]), 2)
        self.assertEqual(len(set(datos["ids"])), 2)

    def test_indices_public_e_internal_quedan_separados(self) -> None:
        publico = reconstruir_indice(
            [self._fragmento(1)],
            perfil="public",
            configuracion=self.configuracion,
            proveedor=self.proveedor,
        )
        interno = reconstruir_indice(
            [self._fragmento(1), self._fragmento(2, "Private")],
            perfil="internal",
            configuracion=self.configuracion,
            proveedor=self.proveedor,
        )

        self.assertNotEqual(publico.directorio, interno.directorio)
        self.assertNotEqual(publico.coleccion, interno.coleccion)
        self.assertEqual(len(self._leer_resultado(publico)["ids"]), 1)
        self.assertEqual(len(self._leer_resultado(interno)["ids"]), 2)

    def test_permite_reconstruir_indice_public_vacio(self) -> None:
        resultado = reconstruir_indice(
            [],
            perfil="public",
            configuracion=self.configuracion,
            proveedor=self.proveedor,
            empresa="EmpresaPrueba",
        )

        self.assertEqual(len(self._leer_resultado(resultado)["ids"]), 0)

    def test_indice_public_rechaza_fragmentos_private(self) -> None:
        with self.assertRaisesRegex(
            ErrorIndiceVectorial,
            "no puede contener fragmentos Private",
        ):
            reconstruir_indice(
                [self._fragmento(1, "Private")],
                perfil="public",
                configuracion=self.configuracion,
                proveedor=self.proveedor,
            )

    def test_rechaza_referencias_duplicadas(self) -> None:
        fragmento = self._fragmento(1)

        with self.assertRaisesRegex(ErrorIndiceVectorial, "duplicadas"):
            reconstruir_indice(
                [fragmento, fragmento],
                perfil="internal",
                configuracion=self.configuracion,
                proveedor=self.proveedor,
            )

    def test_rechaza_mezclar_empresas(self) -> None:
        with self.assertRaisesRegex(ErrorIndiceVectorial, "una sola empresa"):
            reconstruir_indice(
                [self._fragmento(1), self._fragmento(2, empresa="OtraEmpresa")],
                perfil="internal",
                configuracion=self.configuracion,
                proveedor=self.proveedor,
            )


if __name__ == "__main__":
    unittest.main()
