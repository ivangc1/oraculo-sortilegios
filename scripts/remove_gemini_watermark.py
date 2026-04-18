"""Quita la marca de agua ◇ de Gemini (esquina inferior derecha) en un lote de PNG.

Estrategia: muestrea un parche de pergamino limpio de la esquina SUPERIOR
derecha de la misma imagen y lo pega sobre la esquina inferior derecha con
feathering suave. No usa modelos ni IA — puro PIL.

Uso:
    python scripts/remove_gemini_watermark.py <carpeta_entrada> <carpeta_salida>

Idempotente: sobrescribe la salida cada vez.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

# Fracción del ancho/alto de la imagen que ocupa la marca (con margen de seguridad)
PATCH_W_FRAC = 0.10
PATCH_H_FRAC = 0.07
# Desde qué esquina muestrear el parche limpio (SUPERIOR derecha = sin marca)
SAMPLE_FROM = "top_right"


def remove_watermark(src: Path, dst: Path) -> None:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    pw = int(w * PATCH_W_FRAC)
    ph = int(h * PATCH_H_FRAC)

    # Región de la marca (inferior derecha)
    wm_box = (w - pw, h - ph, w, h)

    # Región limpia para muestrear (superior derecha — mismo borde de pergamino)
    if SAMPLE_FROM == "top_right":
        sample_box = (w - pw, 0, w, ph)
    else:
        sample_box = (0, 0, pw, ph)

    patch = img.crop(sample_box)
    # La muestra viene de arriba: invertir verticalmente para que el degradado
    # del pergamino (más claro en el centro, más oscuro en el borde) case mejor
    patch = patch.transpose(Image.FLIP_TOP_BOTTOM)

    # Feathering: máscara con bordes suaves para fundir
    mask = Image.new("L", (pw, ph), 0)
    feather = min(pw, ph) // 8
    # Área central 100% opaca, bordes degradados
    from PIL import ImageDraw, ImageFilter
    draw = ImageDraw.Draw(mask)
    draw.rectangle((feather, feather, pw - feather, ph - feather), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=feather / 2))

    img.paste(patch, wm_box[:2], mask)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "PNG", optimize=True)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"Uso: python {argv[0]} <carpeta_entrada> <carpeta_salida>")
        return 2

    src_dir = Path(argv[1])
    dst_dir = Path(argv[2])

    if not src_dir.is_dir():
        print(f"ERROR: {src_dir} no existe o no es carpeta")
        return 1

    pngs = sorted(p for p in src_dir.iterdir() if p.suffix.lower() == ".png")
    if not pngs:
        print(f"No hay PNG en {src_dir}")
        return 1

    print(f"Procesando {len(pngs)} PNG de {src_dir} -> {dst_dir}")
    for p in pngs:
        dst = dst_dir / p.name
        remove_watermark(p, dst)
        print(f"  OK {p.name}")

    print(f"Hecho. {len(pngs)} imagenes limpias en {dst_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
