"""Pruebas de los servicios usados por Streamlit, sin red ni Gemini."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from Agente.app.generacion import ConfiguracionLLM
from Agente.app.generacion.modelos import RespuestaGenerada
from Agente.app.procesamiento.embeddings import ConfiguracionEmbeddings
from Agente.app.procesamiento.indice_vectorial import ResultadoIndexacion
from Agente.app.recuperacion import FragmentoRecuperado
from Agente.app.servicios.agente import ServicioAgente
from Agente.app.servicios.documentos import (
    EXTENSIONES_SOPORTADAS,
    guardar_documentos,
    listar_documentos,
    listar_empresas,
)
from Agente.app.servicios.indexacion import actualizar_conocimiento


class ArchivoSimulado:
    def __init__(self, nombre: str, contenido: bytes) -> None:
        self.name = nombre
        self._contenido = contenido

    def getvalue(self) -> bytes:
        return self._contenido


class ServiciosInterfazTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temporal.name)
        for empresa in ("EmpresaUno", "EmpresaDos"):
            (self.raiz / empresa / "Public").mkdir(parents=True)
            (self.raiz / empresa / "Private").mkdir()

    def tearDown(self) -> None:
        self.temporal.cleanup()

    @staticmethod
    def _fragmento() -> FragmentoRecuperado:
        return FragmentoRecuperado(
            contenido_markdown="# Sección\n\nContenido ficticio",
            distancia=0.12,
            empresa="EmpresaUno",
            visibilidad="Public",
            ruta_relativa="EmpresaUno/Public/manual.md",
            titulo_seccion="Sección",
            nivel_seccion=1,
            indice_seccion=1,
            indice_fragmento_seccion=1,
            total_fragmentos_seccion=1,
            indice_fragmento_documento=1,
            referencia_fragmento="manual.md#fragmento-1",
        )

    def test_lista_empresas_con_estructura_completa(self) -> None:
        (self.raiz / "NoEsEmpresa").mkdir()

        self.assertEqual(
            listar_empresas(self.raiz),
            ("EmpresaDos", "EmpresaUno"),
        )

    def test_formatos_soportados_estan_centralizados(self) -> None:
        self.assertEqual(
            EXTENSIONES_SOPORTADAS,
            ("md", "markdown", "txt", "docx", "pdf"),
        )

    def test_guarda_y_lista_markdown_en_visibilidad_seleccionada(self) -> None:
        guardados = guardar_documentos(
            [ArchivoSimulado("manual.md", b"# Manual\n\nContenido")],
            "EmpresaUno",
            "Private",
            raiz_agente=self.raiz,
        )
        documentos = listar_documentos(
            "EmpresaUno",
            "Private",
            raiz_agente=self.raiz,
        )

        self.assertEqual(guardados, ("manual.md",))
        self.assertEqual(len(documentos), 1)
        self.assertEqual(documentos[0].nombre, "manual.md")
        self.assertEqual(documentos[0].visibilidad, "Private")

    def test_rechaza_rutas_formatos_no_soportados_y_texto_invalido(self) -> None:
        casos = (
            ("../fuera.md", b"texto", "nombre simple"),
            ("datos.csv", b"a,b", "Formato no soportado"),
            ("legado.doc", b"contenido", "Convierte el archivo a .docx"),
            ("invalido.md", b"\xff\xfe\x00", "UTF-8"),
        )
        for nombre, contenido, mensaje in casos:
            with self.subTest(nombre=nombre):
                with self.assertRaisesRegex(ValueError, mensaje):
                    guardar_documentos(
                        [ArchivoSimulado(nombre, contenido)],
                        "EmpresaUno",
                        "Public",
                        raiz_agente=self.raiz,
                    )

    def test_servicio_devuelve_metricas_del_flujo_completo(self) -> None:
        fragmento = self._fragmento()
        respuesta = RespuestaGenerada(
            texto="Respuesta",
            informacion_encontrada=True,
            fuentes=(),
        )
        servicio = ServicioAgente(
            empresa="EmpresaUno",
            configuracion_embeddings=ConfiguracionEmbeddings(
                modelo="embedding-falso",
                dimensiones=3,
                directorio_vectorial=self.raiz / ".vectorstore",
                clave_api="no-utilizada",
            ),
            proveedor_embeddings=Mock(),
            configuracion_llm=ConfiguracionLLM(
                modelo="llm-falso",
                clave_api="no-utilizada",
            ),
            proveedor_llm=Mock(),
        )

        with (
            patch(
                "Agente.app.servicios.agente.recuperar_fragmentos",
                return_value=[fragmento],
            ) as recuperar,
            patch(
                "Agente.app.servicios.agente.generar_respuesta",
                return_value=respuesta,
            ) as generar,
            patch(
                "Agente.app.servicios.agente.perf_counter",
                side_effect=(10.0, 10.42),
            ),
        ):
            resultado = servicio.consultar("Pregunta", "public", top_k=3)

        self.assertEqual(resultado.empresa, "EmpresaUno")
        self.assertEqual(resultado.perfil, "public")
        self.assertEqual(resultado.modelo, "llm-falso")
        self.assertEqual(resultado.fragmentos, (fragmento,))
        self.assertAlmostEqual(resultado.tiempo_total_segundos, 0.42)
        self.assertEqual(recuperar.call_args.kwargs["top_k"], 3)
        generar.assert_called_once()

    @patch("Agente.app.servicios.indexacion.crear_proveedor_embeddings")
    @patch("Agente.app.servicios.indexacion.cargar_configuracion_embeddings")
    @patch("Agente.app.servicios.indexacion.reconstruir_indice")
    @patch("Agente.app.servicios.indexacion.fragmentar_documentos")
    @patch("Agente.app.servicios.indexacion.extraer_documentos")
    @patch("Agente.app.servicios.indexacion.descubrir_documentos")
    @patch("Agente.app.servicios.indexacion.cargar_configuracion")
    def test_public_actualiza_public_e_internal(
        self,
        cargar_configuracion_mock,
        descubrir_mock,
        extraer_mock,
        fragmentar_mock,
        reconstruir_mock,
        cargar_embeddings_mock,
        crear_proveedor_mock,
    ) -> None:
        cargar_configuracion_mock.return_value = SimpleNamespace()
        descubrir_mock.return_value = []
        extraer_mock.return_value = []
        fragmentar_mock.return_value = []
        cargar_embeddings_mock.return_value = SimpleNamespace()
        crear_proveedor_mock.return_value = Mock()
        reconstruir_mock.side_effect = (
            ResultadoIndexacion(
                "public", "EmpresaUno", "uno_public", self.raiz, 0, 0, 0, 0, 0, True
            ),
            ResultadoIndexacion(
                "internal", "EmpresaUno", "uno_internal", self.raiz, 0, 0, 0, 0, 0, True
            ),
        )

        resultados = actualizar_conocimiento("EmpresaUno", "Public")

        self.assertEqual([resultado.perfil for resultado in resultados], ["public", "internal"])
        self.assertEqual(
            [llamada.args[1] for llamada in reconstruir_mock.call_args_list],
            ["public", "internal"],
        )

    @patch("Agente.app.servicios.indexacion.crear_proveedor_embeddings")
    @patch("Agente.app.servicios.indexacion.cargar_configuracion_embeddings")
    @patch("Agente.app.servicios.indexacion.reconstruir_indice")
    @patch("Agente.app.servicios.indexacion.fragmentar_documentos", return_value=[])
    @patch("Agente.app.servicios.indexacion.extraer_documentos", return_value=[])
    @patch("Agente.app.servicios.indexacion.descubrir_documentos", return_value=[])
    @patch("Agente.app.servicios.indexacion.cargar_configuracion", return_value=SimpleNamespace())
    def test_private_actualiza_solo_internal(
        self,
        cargar_configuracion_mock,
        descubrir_mock,
        extraer_mock,
        fragmentar_mock,
        reconstruir_mock,
        cargar_embeddings_mock,
        crear_proveedor_mock,
    ) -> None:
        cargar_embeddings_mock.return_value = SimpleNamespace()
        crear_proveedor_mock.return_value = Mock()
        reconstruir_mock.return_value = ResultadoIndexacion(
            "internal", "EmpresaUno", "uno_internal", self.raiz, 0, 0, 0, 0, 0, True
        )

        resultados = actualizar_conocimiento("EmpresaUno", "Private")

        self.assertEqual([resultado.perfil for resultado in resultados], ["internal"])


if __name__ == "__main__":
    unittest.main()
