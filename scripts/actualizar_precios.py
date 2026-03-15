#!/usr/bin/env python3
"""
Script principal para actualizar precios de cereales desde todas las fuentes.

Fuentes:
  1. Junta de Castilla y León (Excel semanal) - 10 lonjas
  2. FEDETO / Toledo (HTML) - 1 lonja
  3. Interempresas / Barcelona (HTML) - 1 lonja
  4. Lonja de Sevilla (PDF) - 1 lonja

Frecuencias de actualización:
  - Junta CyL:  Lunes (semanal, ~2 semanas de retraso)
  - Barcelona:   Martes (semanal)
  - Sevilla:     Martes (variable, cada 1-3 semanas)
  - Toledo:      Viernes (quincenal)

Uso:
  python actualizar_precios.py              # Actualiza la semana actual
  python actualizar_precios.py --semana 8   # Actualiza semana específica
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Importar scrapers
from fuentes.jcyl_excel import obtener_precios_jcyl
from fuentes.toledo_fedeto import obtener_precios_toledo
from fuentes.barcelona_interempresas import obtener_precios_barcelona
from fuentes.sevilla_pdf import obtener_precios_sevilla

# Directorio base del proyecto
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "src" / "data"
PRECIOS_DIR = DATA_DIR / "precios"

# Mapeo de IDs del Excel JCyL a nuestros IDs de lonja
MAPEO_LONJAS_JCYL = {
    "Ebro": "ebro",
    "Albacete": "albacete",
    "Ciudad Real": None,  # No la tenemos en lonjas.json
    "Lérida": None,       # No la tenemos (podríamos añadirla)
    "Salamanca": "salamanca",
    "Valladolid": "valladolid",
    "Palencia": None,     # Incluida en valladolid (Lonja de Valladolid y Palencia)
    "Lerma": "burgos",    # Lerma = Lonja de Burgos
    "Segovia": "segovia",
    "León": "leon",
}

# Mapeo de cereales del Excel JCyL a nuestros IDs
MAPEO_CEREALES_JCYL = {
    "Trigo": "trigo",
    "Trigo Duro": None,   # No lo tenemos separado
    "Cebada (+64)": "cebada",
    "Cebada (60-64)": None,  # Usamos solo la +64
    "Maiz seco nac": "maiz",
    "Avena": "avena",
    "Centeno": "centeno",
    "Pipa de girasol": "girasol",
}


def obtener_semana_iso(fecha=None):
    """Devuelve el número de semana ISO de una fecha."""
    if fecha is None:
        fecha = datetime.now()
    return fecha.isocalendar()[1]


def obtener_rango_semana(anio, semana):
    """Devuelve fecha inicio (lunes) y fin (viernes) de una semana ISO."""
    # Primer día del año
    jan4 = datetime(anio, 1, 4)
    # Lunes de la semana 1
    lunes_s1 = jan4 - timedelta(days=jan4.weekday())
    # Lunes de la semana deseada
    lunes = lunes_s1 + timedelta(weeks=semana - 1)
    viernes = lunes + timedelta(days=4)
    return lunes.strftime("%Y-%m-%d"), viernes.strftime("%Y-%m-%d")


def cargar_json_existente(anio, semana):
    """Carga el JSON de una semana si ya existe, sino devuelve estructura vacía."""
    filepath = PRECIOS_DIR / str(anio) / f"semana-{semana:02d}.json"
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    fecha_inicio, fecha_fin = obtener_rango_semana(anio, semana)
    return {
        "semana": semana,
        "anio": anio,
        "campania": f"{anio - 1}-{anio}" if semana < 30 else f"{anio}-{anio + 1}",
        "fechaInicio": fecha_inicio,
        "fechaFin": fecha_fin,
        "precios": {},
    }


def cargar_precios_semana_anterior(anio, semana):
    """Devuelve los precios de la semana anterior como dict {lonja_id: {cereal_id: precio}}."""
    sem_ant = semana - 1
    anio_ant = anio
    if sem_ant == 0:
        sem_ant = 52
        anio_ant = anio - 1
    filepath = PRECIOS_DIR / str(anio_ant) / f"semana-{sem_ant:02d}.json"
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        datos = json.load(f)
    result = {}
    for lonja_id, cereales in datos.get("precios", {}).items():
        result[lonja_id] = {c: v["precio"] for c, v in cereales.items()}
    return result


def integrar_precios(datos_semana, lonja_id, precios_cereal, precios_anteriores=None):
    """
    Integra precios de una lonja en la estructura de datos de la semana.

    precios_cereal: dict de {cereal_id: precio_en_eur_por_tonelada}
    precios_anteriores: dict de {lonja_id: {cereal_id: precio}} de la semana anterior
    """
    if lonja_id not in datos_semana["precios"]:
        datos_semana["precios"][lonja_id] = {}

    existentes = datos_semana["precios"][lonja_id]
    anteriores_lonja = (precios_anteriores or {}).get(lonja_id, {})

    for cereal_id, precio in precios_cereal.items():
        if precio is None:
            continue
        # Si ya existe en la semana actual (segunda ejecución), mantener el anterior guardado
        if cereal_id in existentes:
            anterior = existentes[cereal_id]["anterior"]
        # Si tenemos datos de la semana anterior, usarlos
        elif cereal_id in anteriores_lonja:
            anterior = anteriores_lonja[cereal_id]
        # Fallback: no hay histórico disponible
        else:
            anterior = precio
        variacion = round(precio - anterior, 2)
        datos_semana["precios"][lonja_id][cereal_id] = {
            "precio": round(precio, 2),
            "anterior": round(anterior, 2),
            "variacion": variacion,
        }


def guardar_json(datos_semana):
    """Guarda el JSON de la semana en disco."""
    anio = datos_semana["anio"]
    semana = datos_semana["semana"]
    dir_anio = PRECIOS_DIR / str(anio)
    dir_anio.mkdir(parents=True, exist_ok=True)

    filepath = dir_anio / f"semana-{semana:02d}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(datos_semana, f, ensure_ascii=False, indent=2)

    print(f"  Guardado: {filepath}")


def guardar_ultima_actualizacion(datos_semana):
    """Guarda la fecha y hora de la última actualización."""
    filepath = DATA_DIR / "ultima-actualizacion.json"
    contenido = {
        "fecha": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "semana": datos_semana["semana"],
        "anio": datos_semana["anio"],
        "lonjas": len(datos_semana["precios"]),
        "precios": sum(len(c) for c in datos_semana["precios"].values()),
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)
    print(f"  Guardado: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Actualizar precios de cereales")
    parser.add_argument("--semana", type=int, help="Número de semana ISO (por defecto: actual)")
    parser.add_argument("--anio", type=int, help="Año (por defecto: actual)")
    parser.add_argument("--solo", choices=["jcyl", "toledo", "barcelona", "sevilla"],
                        help="Ejecutar solo una fuente")
    args = parser.parse_args()

    ahora = datetime.now()
    anio = args.anio or ahora.year
    semana = args.semana or obtener_semana_iso(ahora)

    print(f"=== Actualizando precios - Semana {semana}/{anio} ===\n")

    datos_semana = cargar_json_existente(anio, semana)
    precios_anteriores = cargar_precios_semana_anterior(anio, semana)
    errores = []

    # 1. Junta de Castilla y León (10 lonjas)
    if not args.solo or args.solo == "jcyl":
        print("[1/4] Junta de Castilla y León (Excel)...")
        try:
            precios_jcyl = obtener_precios_jcyl(anio, semana)
            if precios_jcyl:
                for nombre_lonja, cereales in precios_jcyl.items():
                    lonja_id = MAPEO_LONJAS_JCYL.get(nombre_lonja)
                    if lonja_id is None:
                        continue
                    precios_mapeados = {}
                    for nombre_cereal, precio in cereales.items():
                        cereal_id = MAPEO_CEREALES_JCYL.get(nombre_cereal)
                        if cereal_id and precio is not None:
                            precios_mapeados[cereal_id] = precio
                    if precios_mapeados:
                        integrar_precios(datos_semana, lonja_id, precios_mapeados, precios_anteriores)
                        print(f"    OK {nombre_lonja} -> {lonja_id}: {len(precios_mapeados)} cereales")
            else:
                print(f"    AVISO: No hay datos disponibles para semana {semana}")
        except Exception as e:
            errores.append(f"JCyL: {e}")
            print(f"    ERROR: {e}")

    # 2. Toledo / FEDETO
    if not args.solo or args.solo == "toledo":
        print("\n[2/4] Toledo / FEDETO (HTML)...")
        try:
            precios_toledo = obtener_precios_toledo()
            if precios_toledo:
                integrar_precios(datos_semana, "toledo", precios_toledo, precios_anteriores)
                print(f"    OK Toledo: {len(precios_toledo)} cereales")
            else:
                print("    AVISO: No se obtuvieron datos")
        except Exception as e:
            errores.append(f"Toledo: {e}")
            print(f"    ERROR: Error: {e}")

    # 3. Barcelona / Interempresas
    if not args.solo or args.solo == "barcelona":
        print("\n[3/4] Barcelona / Interempresas (HTML)...")
        try:
            precios_bcn = obtener_precios_barcelona()
            if precios_bcn:
                integrar_precios(datos_semana, "barcelona", precios_bcn, precios_anteriores)
                print(f"    OK Barcelona: {len(precios_bcn)} cereales")
            else:
                print("    AVISO: No se obtuvieron datos")
        except Exception as e:
            errores.append(f"Barcelona: {e}")
            print(f"    ERROR: Error: {e}")

    # 4. Sevilla / PDF
    if not args.solo or args.solo == "sevilla":
        print("\n[4/4] Sevilla / PDF...")
        try:
            precios_sevilla = obtener_precios_sevilla()
            if precios_sevilla:
                integrar_precios(datos_semana, "sevilla", precios_sevilla, precios_anteriores)
                print(f"    OK Sevilla: {len(precios_sevilla)} cereales")
            else:
                print("    AVISO: No se obtuvieron datos (puede no haber sesión esta semana)")
        except Exception as e:
            errores.append(f"Sevilla: {e}")
            print(f"    ERROR: Error: {e}")

    # Guardar resultado
    print(f"\n--- Resumen ---")
    lonjas_con_datos = len(datos_semana["precios"])
    total_precios = sum(len(c) for c in datos_semana["precios"].values())
    print(f"Lonjas con datos: {lonjas_con_datos}")
    print(f"Precios totales: {total_precios}")

    if errores:
        print(f"\nErrores ({len(errores)}):")
        for e in errores:
            print(f"  - {e}")

    guardar_json(datos_semana)
    guardar_ultima_actualizacion(datos_semana)
    print("\nOK Actualización completada.")


if __name__ == "__main__":
    main()
