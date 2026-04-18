"""Renombra los 42 retratos regenerados a formato NN_Nombre.png.

Convenciones:
- NN con cero a la izquierda (01..72).
- Nombre en grafia canonica sin acentos ni dieresis (Gaap, Raum, Bune, Vine...).
- Corrige #45 Vine (el usuario guardo el archivo como 46 vine por error).
- Corrige typo #59 Orlax -> Oriax.

Uso:
    python scripts/rename_goetia_regen.py <carpeta>

Corre idempotente: si el archivo destino ya existe con el nombre correcto, salta.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Mapa: filename_actual (lower, .strip()) -> (num_correcto, Nombre_canonico)
RENAMES: dict[str, tuple[int, str]] = {
    "03 vassago.png":      (3,  "Vassago"),
    "04 samigina.png":     (4,  "Samigina"),
    "05 marbas.png":       (5,  "Marbas"),
    "06 valefor.png":      (6,  "Valefor"),
    "08 barbatos.png":     (8,  "Barbatos"),
    "11 gusion.png":       (11, "Gusion"),
    "12 sitri.png":        (12, "Sitri"),
    "14 leraje.png":       (14, "Leraje"),
    "16 zepar.png":        (16, "Zepar"),
    "17 botis.png":        (17, "Botis"),
    "18 bathin.png":       (18, "Bathin"),
    "19 sallos.png":       (19, "Sallos"),
    "20 purson.png":       (20, "Purson"),
    "21 marax.png":        (21, "Marax"),
    "22 ipos.png":         (22, "Ipos"),
    "24 naberius.png":     (24, "Naberius"),
    "26 bune.png":         (26, "Bune"),
    "26 buné.png":         (26, "Bune"),
    "30 forneus.png":      (30, "Forneus"),
    "33 gaap.png":         (33, "Gaap"),
    "33 gäap.png":         (33, "Gaap"),
    "37 phenex.png":       (37, "Phenex"),
    "38 halphas.png":      (38, "Halphas"),
    "40 raum.png":         (40, "Raum"),
    "40 räum.png":         (40, "Raum"),
    "41 focalor.png":      (41, "Focalor"),
    "42 vepar.png":        (42, "Vepar"),
    "43 sabnock.png":      (43, "Sabnock"),
    # CORRECCION: el archivo esta numerado como 46 pero es Vine (#45)
    "46 vine.png":         (45, "Vine"),
    "46 viné.png":         (45, "Vine"),
    "48 haagenti.png":     (48, "Haagenti"),
    "49 crocell.png":      (49, "Crocell"),
    "50 furcas.png":       (50, "Furcas"),
    "54 murmur.png":       (54, "Murmur"),
    "57 ose.png":          (57, "Ose"),
    "58 amy.png":          (58, "Amy"),
    # CORRECCION: typo Orlax -> Oriax (#59)
    "59 orlax.png":        (59, "Oriax"),
    "59 oriax.png":        (59, "Oriax"),
    "60 vapula.png":       (60, "Vapula"),
    "61 zagan.png":        (61, "Zagan"),
    "65 andrealphus.png":  (65, "Andrealphus"),
    "66 kimaris.png":      (66, "Kimaris"),
    "68 belial.png":       (68, "Belial"),
    "69 decarabia.png":    (69, "Decarabia"),
    "70 seere.png":        (70, "Seere"),
    "71 dantalion.png":    (71, "Dantalion"),
    "72 andromalius.png":  (72, "Andromalius"),
}


def rename_folder(folder: Path) -> tuple[int, int, list[str]]:
    """Renombra archivos en la carpeta segun RENAMES. Retorna (renamed, skipped, errors)."""
    renamed = 0
    skipped = 0
    errors: list[str] = []

    for src in sorted(folder.iterdir()):
        if src.suffix.lower() != ".png":
            continue
        key = src.name.lower()
        if key not in RENAMES:
            # Puede ser un archivo ya renombrado o algo inesperado
            if "_" in src.stem and src.stem[:2].isdigit():
                skipped += 1  # ya renombrado
            else:
                errors.append(f"sin mapeo: {src.name}")
            continue
        num, nombre = RENAMES[key]
        dst = folder / f"{num:02d}_{nombre}.png"
        if dst.exists() and dst.resolve() != src.resolve():
            errors.append(f"destino ya existe: {dst.name} (origen: {src.name})")
            continue
        src.rename(dst)
        renamed += 1
        print(f"  {src.name} -> {dst.name}")

    return renamed, skipped, errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Uso: python {argv[0]} <carpeta>")
        return 2

    folder = Path(argv[1])
    if not folder.is_dir():
        print(f"ERROR: {folder} no existe")
        return 1

    print(f"Renombrando en {folder}")
    print("=" * 60)
    renamed, skipped, errors = rename_folder(folder)
    print("=" * 60)
    print(f"Renombrados: {renamed} | Ya en formato: {skipped} | Errores: {len(errors)}")
    for e in errors:
        print(f"  ! {e}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
