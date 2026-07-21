"""Fragmentación de secciones Markdown con solapamiento configurable."""

from __future__ import annotations

from collections.abc import Iterable

from .modelos import DocumentoExtraido, FragmentoMarkdown, SeccionMarkdown


TAMANO_MAXIMO_PREDETERMINADO = 1000
SOLAPAMIENTO_PREDETERMINADO = 150
SEPARADORES = ("\n\n", "\n", ". ", " ")


class ErrorFragmentacion(ValueError):
    """Indica que los parámetros o una sección no permiten fragmentar."""


def _validar_parametros(tamano_maximo: int, solapamiento: int) -> None:
    if tamano_maximo <= 0:
        raise ErrorFragmentacion("tamano_maximo debe ser mayor que cero.")
    if solapamiento < 0:
        raise ErrorFragmentacion("solapamiento no puede ser negativo.")
    if solapamiento >= tamano_maximo:
        raise ErrorFragmentacion(
            "solapamiento debe ser menor que tamano_maximo."
        )


def _separar_encabezado(seccion: SeccionMarkdown) -> tuple[str, str]:
    """Separa el encabezado fijo del cuerpo que sí participa en el overlap."""

    if seccion.titulo is None:
        return "", seccion.contenido_markdown

    encabezado, separador, cuerpo = seccion.contenido_markdown.partition("\n")
    if not separador:
        return encabezado, ""
    return encabezado, cuerpo.lstrip("\n")


def _buscar_fin_logico(texto: str, inicio: int, capacidad: int) -> int:
    """Busca el mejor corte antes del límite, priorizando estructura Markdown."""

    limite = min(inicio + capacidad, len(texto))
    if limite == len(texto):
        return limite

    # No conviene crear un fragmento demasiado pequeño solo por encontrar un
    # separador cercano al inicio de la ventana.
    minimo = inicio + max(1, capacidad // 2)
    for separador in SEPARADORES:
        posicion = texto.rfind(separador, minimo, limite)
        if posicion != -1:
            return posicion + len(separador)

    return limite


def _buscar_inicio_solapado(
    texto: str,
    inicio_actual: int,
    fin_actual: int,
    solapamiento: int,
) -> int:
    """Inicia el siguiente cuerpo cerca del overlap, en un límite legible."""

    if solapamiento == 0:
        return fin_actual

    candidato = max(inicio_actual + 1, fin_actual - solapamiento)
    for separador in SEPARADORES:
        posicion = texto.find(separador, candidato, fin_actual)
        siguiente = posicion + len(separador)
        if posicion != -1 and siguiente < fin_actual:
            return siguiente

    return candidato


def _dividir_cuerpo(
    cuerpo: str,
    capacidad: int,
    solapamiento: int,
) -> list[str]:
    """Divide el cuerpo; el encabezado nunca entra en este cálculo."""

    if not cuerpo:
        return [""]
    if len(cuerpo) <= capacidad:
        return [cuerpo]

    partes: list[str] = []
    inicio = 0
    solapamiento_efectivo = min(solapamiento, max(0, capacidad - 1))

    while inicio < len(cuerpo):
        fin = _buscar_fin_logico(cuerpo, inicio, capacidad)
        parte = cuerpo[inicio:fin].strip("\n")
        if parte:
            partes.append(parte)

        if fin >= len(cuerpo):
            break

        nuevo_inicio = _buscar_inicio_solapado(
            cuerpo,
            inicio,
            fin,
            solapamiento_efectivo,
        )
        inicio = max(inicio + 1, nuevo_inicio)

    return partes


def _fragmentar_seccion(
    seccion: SeccionMarkdown,
    tamano_maximo: int,
    solapamiento: int,
) -> list[str]:
    """Devuelve Markdown completo para cada parte de una sección."""

    if len(seccion.contenido_markdown) <= tamano_maximo:
        return [seccion.contenido_markdown]

    encabezado, cuerpo = _separar_encabezado(seccion)
    separacion = "\n\n" if encabezado and cuerpo else ""
    capacidad_cuerpo = tamano_maximo - len(encabezado) - len(separacion)

    if capacidad_cuerpo <= 0:
        raise ErrorFragmentacion(
            f"El encabezado de la sección '{seccion.titulo}' ocupa todo "
            "tamano_maximo."
        )

    cuerpos = _dividir_cuerpo(cuerpo, capacidad_cuerpo, solapamiento)
    return [
        f"{encabezado}{separacion}{parte}" if encabezado else parte
        for parte in cuerpos
    ]


def fragmentar_documento(
    documento: DocumentoExtraido,
    tamano_maximo: int = TAMANO_MAXIMO_PREDETERMINADO,
    solapamiento: int = SOLAPAMIENTO_PREDETERMINADO,
) -> list[FragmentoMarkdown]:
    """Fragmenta un documento sin unir secciones ni perder su procedencia."""

    _validar_parametros(tamano_maximo, solapamiento)
    fragmentos: list[FragmentoMarkdown] = []
    indice_documento = 1

    for indice_seccion, seccion in enumerate(documento.secciones, start=1):
        contenidos = _fragmentar_seccion(
            seccion,
            tamano_maximo,
            solapamiento,
        )
        total_seccion = len(contenidos)

        for indice_en_seccion, contenido in enumerate(contenidos, start=1):
            referencia = (
                f"{documento.ruta_relativa}#seccion-{indice_seccion}"
                f"-fragmento-{indice_en_seccion}"
            )
            fragmentos.append(
                FragmentoMarkdown(
                    contenido_markdown=contenido,
                    empresa=documento.empresa,
                    visibilidad=documento.visibilidad,
                    ruta_relativa=documento.ruta_relativa,
                    titulo_seccion=seccion.titulo,
                    nivel_seccion=seccion.nivel,
                    indice_seccion=indice_seccion,
                    indice_fragmento_seccion=indice_en_seccion,
                    total_fragmentos_seccion=total_seccion,
                    indice_fragmento_documento=indice_documento,
                    referencia_fragmento=referencia,
                )
            )
            indice_documento += 1

    return fragmentos


def fragmentar_documentos(
    documentos: Iterable[DocumentoExtraido],
    tamano_maximo: int = TAMANO_MAXIMO_PREDETERMINADO,
    solapamiento: int = SOLAPAMIENTO_PREDETERMINADO,
) -> list[FragmentoMarkdown]:
    """Fragmenta varios documentos y conserva el orden recibido."""

    _validar_parametros(tamano_maximo, solapamiento)
    resultado: list[FragmentoMarkdown] = []
    for documento in documentos:
        resultado.extend(
            fragmentar_documento(
                documento,
                tamano_maximo=tamano_maximo,
                solapamiento=solapamiento,
            )
        )
    return resultado
