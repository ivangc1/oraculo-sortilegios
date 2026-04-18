"""Descarga las 32 planchas Le Breton canónicas del Ars Goetia (DI 1863).

De los 72 demonios del Ars Goetia, Louis Le Breton ilustró 35 en el
Dictionnaire Infernal (6ª edición, 1863). De esos 35:
  - 32 se usan directamente en el set del bot (este script)
  - 3 se sustituyen por IA por razones editoriales (ver comentarios en
    el diccionario LEBRETON abajo: #20 Pursan, #24 Naberius, #33 Gaap)

Los 37 demonios restantes no fueron ilustrados por Le Breton y se
generan con IA siguiendo el mismo estilo (grabado decimonónico sobre
pergamino envejecido, monocromo).

Uso:
    python scripts/download_lebreton.py

Idempotente: salta archivos que ya existen en la carpeta destino.
Guarda los archivos como NN_Nombre.{jpg,png} en
assets/goetia_portraits_lebreton/.

Fuente: Wikimedia Commons. Todas las imágenes son de dominio público
(Louis Le Breton 1818-1866, obra de 1863, PD-old-70-expired).
"""
from __future__ import annotations

import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = (
    "OraculoSortilegios/1.0 (https://t.me/oraculo_sortilegios_bot; "
    "educational/bot use)"
)
BASE_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/"

# Mapping: numero -> (Nombre_canonico, filename_wikimedia)
#
# Lista de 35 Goetia con plancha Le Breton auténtica en el DI 1863
# (verificado empíricamente en el PDF de Gallica BNF):
#
#   Le Breton DI 1863 ilustra de forma única 35 de los 72 demonios Goetia.
#   Nota: Collin de Plancy unifica Foras/Forras/Furcas en una sola entrada
#   con una sola plancha; asignada a #50 Furcas porque su descripción
#   (viejo con larga barba sobre caballo pálido con lanza) coincide con la
#   del Goetia para Furcas, no para Foras (#31 es "strong man in human shape"
#   sin los rasgos del viejo, por lo que Foras queda sin plancha y se
#   regenera con IA).
#
# Demonios con plancha SIN incluir aquí (3 casos):
#   - #5 Marbas: el archivo Wikimedia "Marbas.jpg" es el sigilo del
#     Goetia 1904, NO una plancha Le Breton. Collin de Plancy no ilustró
#     a Marbas en el DI 1863. Se regenera con IA.
#   - #20 Pursan: tiene plancha Le Breton auténtica (busto en leaf 576),
#     pero es minimalista comparado con la iconografía canónica completa
#     del Goetia (cara de león + víbora + oso + heraldos). Preferimos IA.
#   - #24 Naberius: plancha Le Breton muestra Cerbère tricéfalo, pero
#     Mathers Goetia dice "Black Crane fluttering about the Circle" —
#     preferimos IA que respeta el texto del Goetia.
#   - #33 Gaap: plancha Le Breton es un demonio alado genérico, pero
#     Mathers Goetia dice "going before four great and mighty kings" —
#     preferimos IA que muestra este detalle canónico.
#
# Demonios Goetia que nunca aparecieron ilustrados (37 casos): se
# regeneran con IA siguiendo estilo Dictionnaire Infernal 1863.
LEBRETON: dict[int, tuple[str, str]] = {
    1:  ("Bael",           "Bael.jpg"),
    2:  ("Agares",         "Agares.jpg"),
    7:  ("Amon",           "Amon.png"),
    8:  ("Barbatos",       "Ill_dict_infernal_p0093-79_barbatos.jpg"),
    9:  ("Paimon",         "Paimon.jpg"),
    10: ("Buer",           "Ill_dict_infernal_p0139-123_buer.jpg"),
    13: ("Beleth",         "Byleth.png"),
    15: ("Eligos",         "Abigor.jpg"),
    22: ("Ipos",           "Ipès.png"),
    23: ("Aim",            "Aim_img.jpg"),
    25: ("Glasya-Labolas", "Caacrinolaas.png"),
    27: ("Ronove",         "Ronwe.jpg"),
    28: ("Berith",         "Ill_dict_infernal_p0110-94_berith.jpg"),
    29: ("Astaroth",       "Astaroth.jpg"),
    32: ("Asmoday",        "Asmodeus.jpg"),
    34: ("Furfur",         "Furfur.jpg"),
    35: ("Marchosias",     "Marchocias.jpg"),
    36: ("Stolas",         "Stolas.jpg"),
    39: ("Malphas",        "Malthas.jpg"),
    44: ("Shax",           "Shax.jpg"),
    46: ("Bifrons",        "Ill_dict_infernal_p0114-98_bifrons.jpg"),
    47: ("Uvall",          "Uvall.png"),
    50: ("Furcas",         "Ill_dict_infernal_p0296-280_forcas_demon.jpg"),
    51: ("Balam",          "Balan_(Demon).png"),
    52: ("Alloces",        "Alloces.jpg"),
    53: ("Caim",           "Caim_in_bird_form.jpg"),
    55: ("Orobas",         "Orobas.jpg"),
    56: ("Gremory",        "Gremory.jpg"),
    62: ("Valac",          "Volac.png"),
    63: ("Andras",         "Andras.png"),
    64: ("Haures",         "Ill_dict_infernal_p0294-278_flauros_demon.jpg"),
    67: ("Amdusias",       "Amdusias.jpg"),
}


def download(
    number: int, nombre: str, filename: str, dest_dir: Path, max_retries: int = 5,
) -> tuple[bool, str]:
    """Descarga una lamina de Le Breton.

    Guarda siempre como .png (convierte si hace falta). Retry con backoff en 429.
    """
    # Destino: siempre .png para uniformidad (se convierte al normalizar)
    ext = Path(filename).suffix.lower()
    dest = dest_dir / f"{number:02d}_{nombre}{ext}"

    if dest.exists():
        return True, f"  {number:02d} {nombre} ya existe ({dest.stat().st_size} bytes) - salto"

    url = BASE_URL + urllib.parse.quote(filename)
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()

            # Validar magic bytes basicos
            if not (data.startswith(b"\x89PNG") or data.startswith(b"\xff\xd8\xff")):
                return False, f"  {number:02d} {nombre} ERROR: '{filename}' no es PNG/JPEG ({len(data)} bytes)"

            dest.write_bytes(data)
            return True, f"  {number:02d} {nombre} descargado '{filename}' ({len(data)} bytes)"

        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429:
                wait = 5 * (2 ** attempt)
                print(f"  {number:02d} {nombre} rate limit, esperando {wait}s...")
                time.sleep(wait)
                continue
            return False, f"  {number:02d} {nombre} ERROR HTTP {e.code} en '{filename}': {e}"
        except Exception as e:
            last_error = e
            return False, f"  {number:02d} {nombre} ERROR en '{filename}': {e}"

    return False, f"  {number:02d} {nombre} ERROR tras {max_retries} intentos: {last_error}"


def main() -> int:
    dest_dir = Path(__file__).parent.parent / "assets" / "goetia_portraits_lebreton"
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Descargando {len(LEBRETON)} grabados de Le Breton (DI 1863) a: {dest_dir}")
    print(f"Fuente: Wikimedia Commons (dominio publico)")
    print("=" * 60)

    ok_count = 0
    failures: list[tuple[int, str, str, str]] = []

    for number in sorted(LEBRETON.keys()):
        nombre, filename = LEBRETON[number]
        ok, msg = download(number, nombre, filename, dest_dir)
        print(msg)
        if ok:
            ok_count += 1
        else:
            failures.append((number, nombre, filename, msg))
        time.sleep(1.5)  # rate limit amistoso con Wikimedia

    print("=" * 60)
    print(f"Total: {ok_count}/{len(LEBRETON)} descargados")

    if failures:
        print(f"\n{len(failures)} fallo(s):")
        for num, nom, fname, msg in failures:
            print(f"  Demonio {num} {nom} (archivo '{fname}'): {msg}")
        return 1

    print("\nTodos los grabados descargados correctamente.")
    print(f"Revisa los archivos en {dest_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
