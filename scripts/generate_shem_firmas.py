"""Genera las 72 firmas del Shem HaMephorash como imágenes sobre pergamino.

Cada firma muestra:
- Nombre del coro en capitales pequeñas (SERAFINES, QUERUBINES, etc).
- Nombre hebreo grande (fuente Times New Roman, soporta hebreo).
- Nombre latino en cursiva.
- Atributo divino en texto pequeño.
- Decoración: marco doble, referencia al salmo al pie.

Fondo: textura de pergamino reutilizada del pipeline Goetia.

Uso:
    python scripts/generate_shem_firmas.py

Output: assets/shem_firmas/NN.png   (72 PNG 1024x1536, 2:3 vertical).

Dominio público: nombres del Shem HaMephorash (tradición cabalística,
Éxodo 14:19-21) y fuente Times New Roman de Windows.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
SHEM_DATA = REPO_ROOT / "data" / "shem_datos.py"
PORTRAIT_REF = REPO_ROOT / "assets" / "goetia_portraits" / "03.png"
OUT_DIR = REPO_ROOT / "assets" / "shem_firmas"

SIZE = (1024, 1536)
SEPIA = (232, 218, 188)
INK = (35, 25, 15)
INK_SOFT = (75, 55, 35)

FONT_HEBREW = "C:/Windows/Fonts/times.ttf"
FONT_SERIF = "C:/Windows/Fonts/times.ttf"
FONT_SERIF_ITALIC = "C:/Windows/Fonts/timesi.ttf"


def load_shem() -> list[dict]:
    ns: dict = {}
    with open(SHEM_DATA, encoding="utf-8") as f:
        exec(compile(f.read(), str(SHEM_DATA), "exec"), ns)
    return ns["SHEM"]


def build_parchment_canvas(size: tuple[int, int]) -> Image.Image:
    """Construye un lienzo de pergamino envejecido (reutiliza la técnica del
    pipeline Goetia: imagen IA escalada + desenfoque fuerte)."""
    import numpy as np

    if PORTRAIT_REF.exists():
        src = Image.open(PORTRAIT_REF).convert("RGB")
        canvas = src.resize(size, Image.LANCZOS)
        canvas = canvas.filter(ImageFilter.GaussianBlur(radius=80))
        arr = np.array(canvas, dtype=np.float32)
        mean = np.array(SEPIA, dtype=np.float32)
        arr = mean + (arr - mean) * 1.3
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)
    return Image.new("RGB", size, SEPIA)


def draw_frame(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """Marco doble decorativo (como las láminas del XIX)."""
    outer_margin = 50
    inner_margin = 70
    draw.rectangle(
        (outer_margin, outer_margin, w - outer_margin, h - outer_margin),
        outline=INK, width=3,
    )
    draw.rectangle(
        (inner_margin, inner_margin, w - inner_margin, h - inner_margin),
        outline=INK, width=1,
    )


def center_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    y: int,
    w: int,
    color: tuple[int, int, int],
) -> None:
    """Dibuja texto centrado horizontalmente en y."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (w - tw) // 2 - bbox[0]
    draw.text((x, y), text, font=font, fill=color)


def build_firma(angel: dict, canvas: Image.Image) -> Image.Image:
    """Construye la firma de un ángel sobre el lienzo de pergamino base."""
    img = canvas.copy()
    W, H = img.size
    draw = ImageDraw.Draw(img)

    draw_frame(draw, W, H)

    font_choir = ImageFont.truetype(FONT_SERIF, 44)
    font_number = ImageFont.truetype(FONT_SERIF_ITALIC, 32)
    font_hebrew = ImageFont.truetype(FONT_HEBREW, 280)
    font_latin = ImageFont.truetype(FONT_SERIF_ITALIC, 92)
    font_attr = ImageFont.truetype(FONT_SERIF_ITALIC, 36)
    font_meta = ImageFont.truetype(FONT_SERIF, 28)

    # Número romano arriba a la izquierda (dentro del marco)
    roman = _roman(angel["number"])
    draw.text((95, 95), roman, font=font_number, fill=INK_SOFT)

    # Coro en mayúsculas pequeñas arriba centrado
    center_text(draw, angel["choir"].upper(), font_choir, 160, W, INK)

    # Línea separadora corta
    draw.line((W // 2 - 60, 240, W // 2 + 60, 240), fill=INK_SOFT, width=2)

    # Nombre hebreo enorme en el centro
    hebrew = angel.get("name_hebrew", "")
    if hebrew:
        bbox = draw.textbbox((0, 0), hebrew, font=font_hebrew)
        th = bbox[3] - bbox[1]
        center_text(draw, hebrew, font_hebrew, (H - th) // 2 - 120, W, INK)

    # Nombre latino en cursiva debajo
    name_y = H // 2 + 140
    center_text(draw, angel["name"], font_latin, name_y, W, INK)

    # Atributo en cursiva más abajo (máx ~45 chars, trunca si no)
    attr = angel.get("attribute", "")
    if attr:
        if len(attr) > 48:
            attr = attr[:45] + "..."
        center_text(draw, attr, font_attr, name_y + 130, W, INK_SOFT)

    # Pie: salmo + virtud corta
    psalm = angel.get("psalm", "")
    if psalm:
        center_text(draw, psalm, font_meta, H - 160, W, INK_SOFT)

    # Número decorativo en centro inferior
    center_text(
        draw, f"— {angel['number']} —", font_meta, H - 115, W, INK_SOFT
    )

    return img


def _roman(n: int) -> str:
    """Convierte 1-72 a número romano."""
    vals = [
        (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
        (5, "V"), (4, "IV"), (1, "I"),
    ]
    s = ""
    for v, sym in vals:
        while n >= v:
            s += sym
            n -= v
    return s


def main() -> int:
    if not Path(FONT_HEBREW).exists():
        print(f"ERROR: fuente hebrea no encontrada en {FONT_HEBREW}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shem = load_shem()
    print(f"Generando {len(shem)} firmas del Shem HaMephorash...")

    canvas = build_parchment_canvas(SIZE)

    ok = 0
    for angel in shem:
        try:
            img = build_firma(angel, canvas)
            out = OUT_DIR / f"{angel['number']:02d}.png"
            img.save(out, "PNG", optimize=True)
            ok += 1
            if angel["number"] <= 3 or angel["number"] == 72:
                print(f"  {angel['number']:02d} {angel['name']} ({angel['choir']}) -> {out.name}")
        except Exception as e:
            print(f"  {angel['number']:02d} {angel['name']}: ERROR {e}")

    print("=" * 60)
    print(f"Total: {ok}/{len(shem)} generados")
    print(f"Destino: {OUT_DIR}")
    return 0 if ok == len(shem) else 1


if __name__ == "__main__":
    sys.exit(main())
