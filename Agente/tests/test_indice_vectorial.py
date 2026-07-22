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

    def __init__(self, fallar_en_llamada: int | None = None) -> None:
        self.fallar_en_llamada = fallar_en_llamada
        self.llamadas = 0
        self.tamanos_lote: list[int] = []

    @staticmethod
    def _vector(texto: str) -> list[float]:
        return [
            float(len(texto)),
            float(sum(ord(caracter) for caracter in texto) % 997),
            float(texto.count(" ") + 1),
        ]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.llamadas += 1
        self.tamanos_lote.append(len(texts))
        if self.llamadas == self.fallar_en_llamada:
            raise RuntimeError("Fallo simulado del proveedor")
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
        metadatos_esperados = {
            clave: "" if valor is None else valor
            for clave, valor in fragmento.metadatos().items()
        }
        self.assertEqual(datos["metadatas"][0], metadatos_esperados)

    def test_crea_la_coleccion_con_distancia_coseno(self) -> None:
        resultado = reconstruir_indice(
            [self._fragmento(1)],
            perfil="public",
            configuracion=self.configuracion,
            proveedor=self.proveedor,
        )
        cliente = chromadb.PersistentClient(path=str(resultado.directorio))
        try:
            coleccion = cliente.get_collection(resultado.coleccion)
            self.assertEqual(
                coleccion.configuration_json["hnsw"]["space"],
                "cosine",
            )
        finally:
            cliente.close()

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

    def test_limita_la_prueba_a_cinco_fragmentos(self) -> None:
        fragmentos = [self._fragmento(numero) for numero in range(1, 9)]

        resultado = reconstruir_indice(
            fragmentos,
            perfil="public",
            configuracion=self.configuracion,
            proveedor=self.proveedor,
            limite_fragmentos=5,
        )

        self.assertEqual(resultado.cantidad_fragmentos, 5)
        self.assertFalse(resultado.indexacion_completa)
        self.assertEqual(len(self._leer_resultado(resultado)["ids"]), 5)

    def test_procesa_y_persiste_por_lotes(self) -> None:
        fragmentos = [self._fragmento(numero) for numero in range(1, 6)]
        eventos = []

        resultado = reconstruir_indice(
            fragmentos,
            perfil="public",
            configuracion=self.configuracion,
            proveedor=self.proveedor,
            tamano_lote=2,
            progreso=lambda actual, total, estado, referencia: eventos.append(
                (actual, total, estado, referencia)
            ),
        )

        self.assertEqual(self.proveedor.tamanos_lote, [2, 2, 1])
        self.assertEqual(len(eventos), 5)
        self.assertEqual(eventos[-1][:2], (5, 5))
        self.assertEqual(len(self._leer_resultado(resultado)["ids"]), 5)

    def test_reanuda_sin_repetir_embeddings_guardados(self) -> None:
        fragmentos = [self._fragmento(numero) for numero in range(1, 6)]
        primera_ejecucion = EmbeddingsSimulados()
        reconstruir_indice(
            fragmentos,
            perfil="public",
            configuracion=self.configuracion,
            proveedor=primera_ejecucion,
            limite_fragmentos=2,
        )

        reanudacion = EmbeddingsSimulados()
        resultado = reconstruir_indice(
            fragmentos,
            perfil="public",
            configuracion=self.configuracion,
            proveedor=reanudacion,
            tamano_lote=2,
        )

        self.assertEqual(reanudacion.tamanos_lote, [2, 1])
        self.assertEqual(resultado.sin_cambios, 2)
        self.assertEqual(resultado.nuevos, 3)
        self.assertEqual(len(self._leer_resultado(resultado)["ids"]), 5)

    def test_conserva_indice_y_lotes_previos_ante_un_fallo(self) -> None:
        iniciales = [self._fragmento(1), self._fragmento(2)]
        resultado_inicial = reconstruir_indice(
            iniciales,
            perfil="public",
            configuracion=self.configuracion,
            proveedor=self.proveedor,
        )
        ampliados = [self._fragmento(numero) for numero in range(1, 7)]
        proveedor_con_fallo = EmbeddingsSimulados(fallar_en_llamada=2)

        with self.assertRaisesRegex(RuntimeError, "Fallo simulado"):
            reconstruir_indice(
                ampliados,
                perfil="public",
                configuracion=self.configuracion,
                proveedor=proveedor_con_fallo,
                tamano_lote=2,
            )

        ids = set(self._leer_resultado(resultado_inicial)["ids"])
        self.assertIn(iniciales[0].referencia_fragmento, ids)
        self.assertIn(iniciales[1].referencia_fragmento, ids)
        self.assertEqual(len(ids), 4)

    def test_elimina_obsoletos_solo_despues_de_ejecucion_total(self) -> None:
        iniciales = [self._fragmento(numero) for numero in range(1, 4)]
        reconstruir_indice(
            iniciales,
            perfil="public",
            configuracion=self.configuracion,
            proveedor=self.proveedor,
        )

        parcial = reconstruir_indice(
            [iniciales[0]],
            perfil="public",
            configuracion=self.configuracion,
            proveedor=EmbeddingsSimulados(),
            limite_fragmentos=1,
        )
        self.assertEqual(len(self._leer_resultado(parcial)["ids"]), 3)
        self.assertEqual(parcial.eliminados, 0)

        completa = reconstruir_indice(
            [iniciales[0]],
            perfil="public",
            configuracion=self.configuracion,
            proveedor=EmbeddingsSimulados(),
        )
        self.assertEqual(len(self._leer_resultado(completa)["ids"]), 1)
        self.assertEqual(completa.eliminados, 2)

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
