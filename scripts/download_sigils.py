"""Descarga los 72 sellos del Ars Goetia desde Wikimedia Commons.

Uso:
    python scripts/download_sigils.py

Idempotente: salta archivos que ya existen en assets/goetia_sigils/.
Los archivos se guardan como 01.png, 02.png, ..., 72.png por número de demonio.

Fuente: Wikimedia Commons, categoría "Sigils of demons". Todas las imágenes
son de dominio público (publicadas antes de 1923 o sin copyright vigente).
"""
from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = (
    "OraculoSortilegios/1.0 (https://t.me/oraculo_sortilegios_bot; "
    "educational/bot use)"
)
BASE_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/"

# Mapping: número (1-72) → filename en Wikimedia Commons
SIGILS: dict[int, str] = {
    1: "01-Bael_seal.png",
    2: "02-Agares_seal.png",
    3: "03-Vassago_seal.png",
    4: "04-Samigina_seal.png",
    5: "05-Marbas_seal.png",
    6: "06-Valefor_seal.png",
    7: "07-Amon_seal.png",
    8: "08-Barbatos_seal.png",
    9: "09-Paimon_seal01.png",
    10: "10-Buer_seal.png",
    11: "11-Gusion_seal.png",
    12: "12-Sitri_seal.png",
    13: "13-Beleth_seal01.png",
    14: "14-Leraie_seal.png",
    15: "15-Eligos_seal.png",
    16: "16-Zepar_seal.png",
    17: "17-Botis_seal.png",
    18: "18-Bathin_seal01.png",
    19: "19-Sallos_seal.png",
    20: "20-Purson_seal.png",
    21: "21-Marax_seal.png",
    22: "22-Ipos_seal.png",
    23: "23-Aim_seal.png",
    24: "24-Naberius_seal.png",
    25: "25-Glasya-Labolas_seal.png",
    26: "26-Bune_seal01.png",
    27: "27-Ronove_seal.png",
    28: "28-Berith_seal.png",
    29: "Astaroth_Seal.png",  # sin número prefijado en Wikimedia
    30: "30-Forneus_seal.png",
    31: "31-Foras_seal.png",
    32: "32-Asmoday_seal.png",
    33: "33-Gaap_seal.png",
    34: "34-Furfur_seal.png",
    35: "35-Marchosias_seal.png",
    36: "36-Stolas_seal.png",
    37: "37-Phenex_seal.png",
    38: "38-Halphus_seal.png",
    39: "39-Malphas.png",  # sin "_seal"
    40: "40-Raum_seal.png",
    41: "41-Focalor_seal.png",
    42: "42-Vepar_seal01.png",
    43: "43-Sabnock_seal.png",
    44: "44-Shax_seal.png",
    45: "45-Vine_seal.png",
    46: "46-Bifrons_seal.png",
    47: "47-Vual_seal01.png",
    48: "48-Haagenti_seal.png",
    49: "49-Crocell_seal.png",
    50: "50-Furcas_seal.png",
    51: "51-Balam_seal.png",
    52: "52-Alloces_seal.png",
    53: "53-Camio_seal.png",
    54: "54-Murmur_seal.png",
    55: "55-Orobas_seal.png",
    56: "56-Gremory_seal.png",
    57: "57-Ose_seal.png",
    58: "58-Amy_seal.png",
    59: "59-Orias_seal.png",
    60: "60-Vapula_seal.png",
    61: "61-Zagan_seal.png",
    62: "62-Valac_seal.png",
    63: "63-Andras_seal.png",
    64: "64-Haures_seal.png",
    65: "65-Andrealphus_seal.png",
    66: "66-Cimeies_seal.png",
    67: "67-Amdusias_seal.png",
    68: "68-Belial_seal.png",
    69: "Decarabia_seal.png",  # sin número prefijado
    70: "70-Seere_seal01.png",
    71: "71-Dantalion_seal.png",
    72: "72-Andromalius_seal.png",
}


def download_sigil(
    number: int, filename: str, dest_dir: Path, max_retries: int = 5,
) -> tuple[bool, str]:
    """Descarga un sello del Ars Goetia.

    Hace retry con backoff exponencial en errores 429 (rate limit).

    Returns:
        (ok, mensaje_estado)
    """
    dest = dest_dir / f"{number:02d}.png"
    if dest.exists():
        return True, f"  {number:02d} ya existe ({dest.stat().st_size} bytes) — salto"

    url = BASE_URL + filename
    last_error = None

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()

            # Validar que es PNG válido
            if not data.startswith(b"\x89PNG"):
                return False, f"  {number:02d} ERROR: '{filename}' no es PNG ({len(data)} bytes)"

            dest.write_bytes(data)
            return True, f"  {number:02d} descargado '{filename}' ({len(data)} bytes)"

        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429:
                # Rate limit: backoff exponencial 5s, 10s, 20s, 40s, 80s
                wait = 5 * (2 ** attempt)
                print(f"  {number:02d} rate limit, esperando {wait}s antes de reintentar...")
                time.sleep(wait)
                continue
            # Otro error HTTP: no reintentar
            return False, f"  {number:02d} ERROR HTTP {e.code} en '{filename}': {e}"
        except Exception as e:
            last_error = e
            return False, f"  {number:02d} ERROR al descargar '{filename}': {e}"

    return False, f"  {number:02d} ERROR tras {max_retries} intentos: {last_error}"


def main() -> int:
    dest_dir = Path(__file__).parent.parent / "assets" / "goetia_sigils"
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Descargando 72 sellos del Ars Goetia a: {dest_dir}")
    print(f"Fuente: Wikimedia Commons (dominio público)")
    print("=" * 60)

    ok_count = 0
    failures: list[tuple[int, str, str]] = []

    for number in sorted(SIGILS.keys()):
        filename = SIGILS[number]
        ok, msg = download_sigil(number, filename, dest_dir)
        print(msg)
        if ok:
            ok_count += 1
        else:
            failures.append((number, filename, msg))
        time.sleep(1.5)  # Rate limit amistoso con Wikimedia (evita 429)

    print("=" * 60)
    print(f"Total: {ok_count}/72 descargados")

    if failures:
        print(f"\n{len(failures)} fallo(s):")
        for num, fname, msg in failures:
            print(f"  Demonio {num} (archivo '{fname}'): {msg}")
        print(
            "\nPara corregir: edita el diccionario SIGILS en este script con "
            "el filename correcto desde commons.wikimedia.org y re-ejecuta."
        )
        return 1

    print("\nTodos los sellos descargados correctamente.")
    print(f"Revisa los archivos en {dest_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
