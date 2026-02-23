"""
Scraper: Lonja de Sevilla - PDFs de cotizaciones.

Fuente: https://www.lonjadesevilla.com/cotizaciones/
Frecuencia: Variable (cada 1-3 semanas, siempre martes).
Formato: PDF con texto de precios (no tablas HTML).

El PDF contiene secciones por producto (TRIGO, CEBADA, MAIZ, etc.)
con lineas tipo:
  "Pienso IMPORTACION Origen Puerto 212 2 BAJO 214"
  "Nacional 204 2 BAJO 206"
  "Igual y mas de 64 192 BAJO 192"

Precios en: EUR/Tonelada
"""

import re
import tempfile
import os
import requests
from bs4 import BeautifulSoup

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

INDEX_URL = "https://www.lonjadesevilla.com/cotizaciones/"


def _obtener_url_ultimo_pdf():
    """Busca la URL del PDF mas reciente en la web de la Lonja de Sevilla."""
    resp = requests.get(INDEX_URL, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    for enlace in soup.find_all("a", href=True):
        href = enlace["href"]
        if href.lower().endswith(".pdf") and "comision" in href.lower():
            if not href.startswith("http"):
                href = "https://www.lonjadesevilla.com" + href
            return href

    return None


def _descargar_pdf(url):
    """Descarga un PDF a un archivo temporal."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(resp.content)
    tmp.close()
    return tmp.name


def _parsear_pdf(filepath):
    """
    Extrae precios de cereales del PDF de la Lonja de Sevilla.

    El texto del PDF tiene secciones por producto. Buscamos precios
    "Nacional" o "Pienso" para cada cereal, que son precios en origen.
    """
    if not HAS_PDFPLUMBER:
        raise ImportError("pdfplumber no instalado. Instala con: pip install pdfplumber")

    precios = {}

    with pdfplumber.open(filepath) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texto_completo += t + "\n"

    if not texto_completo:
        return None

    lineas = texto_completo.split("\n")

    # Estado: que producto estamos leyendo actualmente
    producto_actual = None

    for linea in lineas:
        linea_strip = linea.strip()
        linea_upper = linea_strip.upper()

        # Detectar cabeceras de producto
        if linea_upper.startswith("TRIGO"):
            producto_actual = "trigo"
        elif linea_upper.startswith("CEBADA"):
            producto_actual = "cebada"
        elif "MAIZ" in linea_upper or "MAIZ" in linea_upper.replace("I", "I"):
            if linea_upper.startswith("MAIZ") or linea_upper.startswith("MA"):
                producto_actual = "maiz"
        elif linea_upper.startswith("AVENA"):
            producto_actual = "avena"
        elif linea_upper.startswith("TRITICALE"):
            producto_actual = "triticale"
        elif linea_upper.startswith("GIRASOL"):
            producto_actual = "girasol"
        elif linea_upper.startswith("COLZA"):
            producto_actual = "colza"
        elif linea_upper.startswith("CENTENO"):
            producto_actual = "centeno"
        elif linea_upper.startswith("HABAS") or linea_upper.startswith("GUISANTES"):
            producto_actual = None
        elif linea_upper.startswith("VOLUMEN") or linea_upper.startswith("NOTA"):
            producto_actual = None

        if producto_actual is None or producto_actual in precios:
            continue

        linea_lower = linea_strip.lower()

        # Ignorar lineas de importacion (queremos precios nacionales/en origen)
        if "importacion" in linea_lower:
            continue

        # Determinar si la linea es relevante segun el producto
        es_relevante = False
        if producto_actual == "trigo":
            # "Pienso" sin "IMPORTACION" = trigo pienso nacional
            es_relevante = "pienso" in linea_lower
        elif producto_actual == "cebada":
            # "Igual y mas de 64" = cebada de calidad standard
            es_relevante = "64" in linea_lower or "nacional" in linea_lower
        elif producto_actual in ("maiz", "avena", "triticale", "centeno"):
            es_relevante = "nacional" in linea_lower
        elif producto_actual == "girasol":
            es_relevante = "convencional" in linea_lower
        elif producto_actual == "colza":
            # Colza suele tener una sola linea con precio
            es_relevante = bool(re.search(r'\d{3}', linea_strip))

        if not es_relevante:
            continue

        # Extraer primer numero que parezca precio (3 digitos)
        numeros = re.findall(r'\b(\d{3})\b', linea_strip)
        for num_str in numeros:
            try:
                valor = float(num_str)
                if 100 <= valor <= 800:
                    precios[producto_actual] = valor
                    break
            except (ValueError, TypeError):
                continue

    return precios


def obtener_precios_sevilla():
    """
    Obtiene los precios mas recientes de la Lonja de Sevilla.

    Returns:
        dict: {cereal_id: precio_eur_tonelada} o None si falla.
    """
    print("    Buscando ultimo PDF de Sevilla...")
    url_pdf = _obtener_url_ultimo_pdf()

    if url_pdf is None:
        print("    No se encontro PDF reciente")
        return None

    print(f"    Descargando: {url_pdf}")
    filepath = _descargar_pdf(url_pdf)

    try:
        precios = _parsear_pdf(filepath)
        return precios if precios else None
    finally:
        os.unlink(filepath)
