"""Pruebas de respuestas fundamentadas sin llamadas reales a Gemini."""

import unittest

from Agente.app.generacion import (
    FALLBACK_SIN_INFORMACION,
    ErrorGeneracion,
    SalidaLLM,
    generar_respuesta,
)
from Agente.app.recuperacion import FragmentoRecuperado


class LLMSimulado:
    def __init__(self, salida: SalidaLLM, error: Exception | None = None) -> None:
        self.salida = salida
        self.error = error
        self.llamadas: list[tuple[str, str]] = []

    def generar(self, instruccion_sistema: str, mensaje_usuario: str) -> SalidaLLM:
        self.llamadas.append((instruccion_sistema, mensaje_usuario))
        if self.error:
            raise self.error
        return self.salida


class GeneracionTests(unittest.TestCase):
    @staticmethod
    def _fragmento(
        numero: int,
        *,
        archivo: str = "BaseInstitucional.md",
        seccion: str | None = "Misión",
        visibilidad: str = "Public",
    ) -> FragmentoRecuperado:
        ruta = f"AlianzaF1/{visibilidad}/{archivo}"
        return FragmentoRecuperado(
            contenido_markdown=f"## {seccion or 'Contenido'}\n\n- Dato documental {numero}",
            distancia=0.1 * numero,
            empresa="AlianzaF1",
            visibilidad=visibilidad,
            ruta_relativa=ruta,
            titulo_seccion=seccion,
            nivel_seccion=2,
            indice_seccion=numero,
            indice_fragmento_seccion=1,
            total_fragmentos_seccion=1,
            indice_fragmento_documento=numero,
            referencia_fragmento=f"{ruta}#seccion-{numero}-fragmento-1",
        )

    def test_no_invoca_llm_cuando_no_hay_fragmentos(self) -> None:
        proveedor = LLMSimulado(SalidaLLM("No debe usarse", True, (1,)))

        respuesta = generar_respuesta("Pregunta sin contexto", [], proveedor)

        self.assertEqual(respuesta.texto, FALLBACK_SIN_INFORMACION)
        self.assertFalse(respuesta.informacion_encontrada)
        self.assertEqual(respuesta.fuentes, ())
        self.assertEqual(proveedor.llamadas, [])

    def test_envia_pregunta_markdown_y_metadatos_al_llm(self) -> None:
        fragmento = self._fragmento(1)
        proveedor = LLMSimulado(SalidaLLM("Respuesta respaldada", True, (1,)))

        generar_respuesta("¿Cuál es la misión?", [fragmento], proveedor)

        instruccion, mensaje = proveedor.llamadas[0]
        self.assertIn("\u00fanicamente", instruccion)
        self.assertIn("¿Cuál es la misión?", mensaje)
        self.assertIn("## Misión", mensaje)
        self.assertIn("[Fuente 1]", mensaje)
        self.assertIn(fragmento.referencia_fragmento, mensaje)

    def test_construye_citas_desde_metadatos_validados(self) -> None:
        primero = self._fragmento(1)
        segundo = self._fragmento(
            2,
            archivo="BasePropuestasComercial.md",
            seccion="Servicios",
        )
        proveedor = LLMSimulado(
            SalidaLLM("La respuesta está en ambos documentos.", True, (2, 1))
        )

        respuesta = generar_respuesta(
            "Pregunta",
            [primero, segundo],
            proveedor,
        )

        self.assertTrue(respuesta.informacion_encontrada)
        self.assertEqual(
            [fuente.archivo for fuente in respuesta.fuentes],
            ["BasePropuestasComercial.md", "BaseInstitucional.md"],
        )
        self.assertIn("Sección: Servicios", respuesta.texto)
        self.assertIn(segundo.referencia_fragmento, respuesta.texto)

    def test_elimina_citas_duplicadas_conservando_el_orden(self) -> None:
        fragmento = self._fragmento(1)
        proveedor = LLMSimulado(SalidaLLM("Respuesta", True, (1, 1, 1)))

        respuesta = generar_respuesta("Pregunta", [fragmento], proveedor)

        self.assertEqual(len(respuesta.fuentes), 1)
        self.assertEqual(respuesta.texto.count("- BaseInstitucional.md"), 1)

    def test_aplica_fallback_si_modelo_no_encuentra_informacion(self) -> None:
        proveedor = LLMSimulado(SalidaLLM("No sé", False, ()))

        respuesta = generar_respuesta(
            "Pregunta",
            [self._fragmento(1)],
            proveedor,
        )

        self.assertEqual(respuesta.texto, FALLBACK_SIN_INFORMACION)
        self.assertNotIn("contact", respuesta.texto.casefold())

    def test_aplica_fallback_si_no_hay_fuentes(self) -> None:
        proveedor = LLMSimulado(SalidaLLM("Respuesta sin respaldo", True, ()))

        respuesta = generar_respuesta(
            "Pregunta",
            [self._fragmento(1)],
            proveedor,
        )

        self.assertEqual(respuesta.texto, FALLBACK_SIN_INFORMACION)

    def test_aplica_fallback_si_llm_inventa_una_fuente(self) -> None:
        proveedor = LLMSimulado(SalidaLLM("Respuesta", True, (3,)))

        respuesta = generar_respuesta(
            "Pregunta",
            [self._fragmento(1)],
            proveedor,
        )

        self.assertEqual(respuesta.texto, FALLBACK_SIN_INFORMACION)
        self.assertEqual(respuesta.fuentes, ())

    def test_no_inventa_pagina_fecha_ni_contactos(self) -> None:
        proveedor = LLMSimulado(SalidaLLM("Respuesta documental", True, (1,)))

        respuesta = generar_respuesta(
            "Pregunta",
            [self._fragmento(1)],
            proveedor,
        )

        texto = respuesta.texto.casefold()
        self.assertNotIn("página", texto)
        self.assertNotIn("fecha", texto)
        self.assertNotIn("contact", texto)

    def test_pregunta_vacia_produce_error_claro(self) -> None:
        proveedor = LLMSimulado(SalidaLLM("Respuesta", True, (1,)))

        with self.assertRaisesRegex(ErrorGeneracion, "pregunta"):
            generar_respuesta("   ", [self._fragmento(1)], proveedor)

    def test_propaga_fallo_del_proveedor(self) -> None:
        proveedor = LLMSimulado(
            SalidaLLM("", False, ()),
            error=RuntimeError("Fallo simulado del LLM"),
        )

        with self.assertRaisesRegex(RuntimeError, "Fallo simulado"):
            generar_respuesta("Pregunta", [self._fragmento(1)], proveedor)


if __name__ == "__main__":
    unittest.main()
