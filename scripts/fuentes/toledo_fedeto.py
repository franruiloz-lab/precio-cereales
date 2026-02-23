"""
Scraper: Lonja de Toledo / FEDETO.

Fuente: https://www.fedeto.es/lonja/cereales.htm
Frecuencia: Quincenal (viernes).
Formato: Tabla HTML estática.

Precios en: €/Tn en origen.
"""

import re
import requests
from bs4 import BeautifulSoup

URL = "https://www.fedeto.es/lonja/cereales.htm"

# Mapeo de nombres en la tabla de FEDETO a nuestros IDs de cereal
MAPEO_CEREALES = {
    "maiz secadero": "maiz",
    "maíz secadero": "maiz",
    "cebada pienso": "cebada",
    "cebada pienso (+62)": "cebada",
    "cebada pienso (-62)": None,  # Solo usamos la de más peso
    "avena rubia": "avena",
    "avena de pienso": None,
    "trigo pienso": "trigo",
    "trigo fuerza": None,  # Tipo diferente
    "trigo duro": None,
    "triticale": "triticale",
    "centeno": "centeno",
    "girasol": "girasol",
    "colza": "colza",
}


def obtener_precios_toledo():
    """
    Obtiene los precios más recientes de la Lonja de Toledo (FEDETO).

    Returns:
        dict: {cereal_id: precio_eur_tonelada} o None si falla.
    """
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding

    soup = BeautifulSoup(resp.text, "html.parser")

    # Buscar la tabla de precios
    tablas = soup.find_all("table")
    if not tablas:
        print("    No se encontraron tablas en la página")
        return None

    precios = {}

    for tabla in tablas:
        filas = tabla.find_all("tr")
        for fila in filas:
            celdas = fila.find_all(["td", "th"])
            if len(celdas) < 2:
                continue

            # Primera celda: nombre del producto
            nombre_raw = celdas[0].get_text(strip=True).lower()

            # Buscar coincidencia en nuestro mapeo
            cereal_id = None
            for patron, cid in MAPEO_CEREALES.items():
                if patron in nombre_raw:
                    cereal_id = cid
                    break

            if cereal_id is None:
                continue

            # Buscar el precio más reciente (última columna con número)
            precio = None
            for celda in reversed(celdas[1:]):
                texto = celda.get_text(strip=True)
                # Limpiar texto: quitar +, -, =, espacios
                texto_limpio = re.sub(r'[+\-=\s]', '', texto)
                texto_limpio = texto_limpio.replace(',', '.')
                try:
                    valor = float(texto_limpio)
                    if 50 < valor < 1000:  # Rango razonable €/t
                        precio = valor
                        break
                except (ValueError, TypeError):
                    continue

            if precio and cereal_id not in precios:
                precios[cereal_id] = precio

    return precios if precios else None
