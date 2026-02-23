"""
Scraper: Lonja de Barcelona / Interempresas.net.

Fuente: https://www.interempresas.net/ovino/316017-Lonja-de-Cereales-de-Barcelona-Cotizaciones-de-Cereal.html
Frecuencia: Semanal (martes).
Formato: Página índice con enlaces a artículos semanales. Cada artículo tiene tabla HTML.

Precios en: €/t
"""

import re
import requests
from bs4 import BeautifulSoup

INDEX_URL = (
    "https://www.interempresas.net/ovino/316017-Lonja-de-Cereales-de-Barcelona-"
    "Cotizaciones-de-Cereal.html"
)

# Mapeo de nombres en la tabla a nuestros IDs
MAPEO_CEREALES = {
    "trigo pienso": "trigo",
    "trigo fuerza": None,
    "trigo duro": None,
    "cebada pienso": "cebada",
    "cebada nacional": "cebada",
    "maiz": "maiz",
    "maíz": "maiz",
    "corn gluten": None,
    "avena": "avena",
    "centeno": "centeno",
    "colza": "colza",
    "girasol": "girasol",
    "triticale": "triticale",
    "sorgo": None,
    "mijo": None,
}


def _obtener_url_ultimo_articulo():
    """Obtiene la URL del artículo más reciente desde la página índice."""
    resp = requests.get(INDEX_URL, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Los hrefs son relativos tipo "622829-Lonja-de-...html?R=316017"
    # Necesitan el prefijo /ovino/Articulos/ para la URL completa
    for enlace in soup.find_all("a", href=True):
        href = enlace["href"]
        texto = enlace.get_text(strip=True)
        if "Semana" in texto and "Barcelona" in texto:
            if not href.startswith("http"):
                href = f"https://www.interempresas.net/ovino/Articulos/{href}"
            return href

    # Plan B: buscar por patron Lonja-de-Cereales-de-Barcelona en href
    for enlace in soup.find_all("a", href=True):
        href = enlace["href"]
        if "Lonja-de-Cereales-de-Barcelona" in href and not href.startswith("http"):
            href = f"https://www.interempresas.net/ovino/Articulos/{href}"
            return href

    return None


def _parsear_articulo(url):
    """Parsea un artículo de Interempresas para extraer los precios."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Buscar tablas con precios
    tablas = soup.find_all("table")
    precios = {}

    for tabla in tablas:
        filas = tabla.find_all("tr")
        for fila in filas:
            celdas = fila.find_all(["td", "th"])
            if len(celdas) < 3:
                continue

            # Primera celda: nombre del producto
            nombre_raw = celdas[0].get_text(strip=True).lower()

            # Buscar coincidencia
            cereal_id = None
            for patron, cid in MAPEO_CEREALES.items():
                if patron in nombre_raw:
                    cereal_id = cid
                    break

            if cereal_id is None or cereal_id in precios:
                continue

            # Buscar precio "Actual" (normalmente en la 3ª o 4ª celda)
            for celda in celdas[1:]:
                texto = celda.get_text(strip=True)
                texto_limpio = texto.replace(',', '.').replace('€', '').strip()
                # Eliminar caracteres no numéricos excepto punto
                texto_limpio = re.sub(r'[^\d.]', '', texto_limpio)
                try:
                    valor = float(texto_limpio)
                    if 100 < valor < 800:  # Rango razonable €/t
                        precios[cereal_id] = valor
                        break
                except (ValueError, TypeError):
                    continue

    return precios


def obtener_precios_barcelona():
    """
    Obtiene los precios más recientes de la Lonja de Barcelona.

    Returns:
        dict: {cereal_id: precio_eur_tonelada} o None si falla.
    """
    print("    Buscando último artículo de Barcelona...")
    url_articulo = _obtener_url_ultimo_articulo()

    if url_articulo is None:
        print("    No se encontró artículo reciente")
        return None

    print(f"    Parseando: {url_articulo}")
    precios = _parsear_articulo(url_articulo)

    return precios if precios else None
