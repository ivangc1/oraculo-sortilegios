"""Renderer de runas Elder Futhark: trazos vectoriales Pillow sobre textura piedra.

Cada runa se define como lista de segmentos de línea en coordenadas normalizadas (0-1).
Efecto tallado: sombra desplazada = profundidad.
Zero assets de fuentes, 100% código propio, AGPL-compatible.
"""

from io import BytesIO
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

# Coordenadas normalizadas (0-1) para cada runa del Elder Futhark.
# Cada runa es una lista de segmentos: ((x1,y1), (x2,y2))
RUNE_PATHS: dict[str, list[tuple[tuple[float, float], tuple[float, float]]]] = {
    "fehu": [
        ((0.5, 0.0), (0.5, 1.0)),
        ((0.5, 0.15), (0.85, 0.30)),
        ((0.5, 0.40), (0.80, 0.55)),
    ],
    "uruz": [
        ((0.25, 0.0), (0.25, 1.0)),
        ((0.25, 0.0), (0.75, 0.35)),
        ((0.75, 0.35), (0.75, 1.0)),
    ],
    "thurisaz": [
        ((0.30, 0.0), (0.30, 1.0)),
        ((0.30, 0.30), (0.80, 0.50)),
        ((0.80, 0.50), (0.30, 0.70)),
    ],
    "ansuz": [
        ((0.50, 0.0), (0.50, 1.0)),
        ((0.50, 0.20), (0.15, 0.45)),
        ((0.50, 0.45), (0.15, 0.70)),
    ],
    "raidho": [
        ((0.30, 0.0), (0.30, 1.0)),
        ((0.30, 0.0), (0.75, 0.0)),
        ((0.75, 0.0), (0.30, 0.50)),
        ((0.30, 0.50), (0.75, 1.0)),
    ],
    "kenaz": [
        ((0.25, 0.0), (0.75, 0.50)),
        ((0.75, 0.50), (0.25, 1.0)),
    ],
    "gebo": [
        ((0.15, 0.15), (0.85, 0.85)),
        ((0.85, 0.15), (0.15, 0.85)),
    ],
    "wunjo": [
        ((0.30, 0.0), (0.30, 1.0)),
        ((0.30, 0.0), (0.75, 0.25)),
        ((0.75, 0.25), (0.30, 0.50)),
    ],
    "hagalaz": [
        ((0.25, 0.0), (0.25, 1.0)),
        ((0.75, 0.0), (0.75, 1.0)),
        ((0.25, 0.35), (0.75, 0.65)),
    ],
    "nauthiz": [
        ((0.50, 0.0), (0.50, 1.0)),
        ((0.25, 0.35), (0.75, 0.65)),
    ],
    "isa": [
        ((0.50, 0.0), (0.50, 1.0)),
    ],
    "jera": [
        ((0.50, 0.0), (0.80, 0.25)),
        ((0.80, 0.25), (0.50, 0.50)),
        ((0.50, 0.50), (0.20, 0.75)),
        ((0.20, 0.75), (0.50, 1.0)),
    ],
    "eihwaz": [
        ((0.50, 0.0), (0.50, 1.0)),
        ((0.50, 0.25), (0.80, 0.10)),
        ((0.50, 0.75), (0.20, 0.90)),
    ],
    "perthro": [
        ((0.25, 0.0), (0.25, 1.0)),
        ((0.25, 0.0), (0.75, 0.25)),
        ((0.75, 0.25), (0.25, 0.50)),
    ],
    "algiz": [
        ((0.50, 1.0), (0.50, 0.30)),
        ((0.50, 0.30), (0.20, 0.0)),
        ((0.50, 0.30), (0.80, 0.0)),
    ],
    "sowilo": [
        ((0.25, 0.0), (0.75, 0.35)),
        ((0.75, 0.35), (0.25, 0.65)),
        ((0.25, 0.65), (0.75, 1.0)),
    ],
    "tiwaz": [
        ((0.50, 0.0), (0.50, 1.0)),
        ((0.50, 0.0), (0.15, 0.30)),
        ((0.50, 0.0), (0.85, 0.30)),
    ],
    "berkano": [
        ((0.25, 0.0), (0.25, 1.0)),
        ((0.25, 0.0), (0.75, 0.25)),
        ((0.75, 0.25), (0.25, 0.50)),
        ((0.25, 0.50), (0.75, 0.75)),
        ((0.75, 0.75), (0.25, 1.0)),
    ],
    "ehwaz": [
        ((0.25, 0.0), (0.25, 1.0)),
        ((0.75, 0.0), (0.75, 1.0)),
        ((0.25, 0.30), (0.75, 0.50)),
        ((0.25, 0.50), (0.75, 0.70)),
    ],
    "mannaz": [
        ((0.20, 0.0), (0.20, 1.0)),
        ((0.80, 0.0), (0.80, 1.0)),
        ((0.20, 0.0), (0.50, 0.35)),
        ((0.80, 0.0), (0.50, 0.35)),
    ],
    "laguz": [
        ((0.35, 0.0), (0.35, 1.0)),
        ((0.35, 0.0), (0.80, 0.40)),
    ],
    "ingwaz": [
        ((0.50, 0.0), (0.85, 0.50)),
        ((0.85, 0.50), (0.50, 1.0)),
        ((0.50, 1.0), (0.15, 0.50)),
        ((0.15, 0.50), (0.50, 0.0)),
    ],
    "dagaz": [
        ((0.15, 0.0), (0.15, 1.0)),
        ((0.85, 0.0), (0.85, 1.0)),
        ((0.15, 0.0), (0.85, 1.0)),
        ((0.15, 1.0), (0.85, 0.0)),
    ],
    "othala": [
        ((0.50, 0.0), (0.85, 0.30)),
        ((0.85, 0.30), (0.50, 0.60)),
        ((0.50, 0.60), (0.15, 0.30)),
        ((0.15, 0.30), (0.50, 0.0)),
        ((0.50, 0.60), (0.25, 1.0)),
        ((0.50, 0.60), (0.75, 1.0)),
    ],
}

# Colores del efecto tallado en piedra
_SHADOW_COLOR = (40, 40, 40)
_STROKE_COLOR = (220, 200, 160)
_STONE_BG = (90, 85, 78)
_SHADOW_OFFSET = 2
_STROKE_WIDTH = 6
_SHADOW_WIDTH = 8

_FONT_PATH = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSans-Regular.ttf"


def _create_stone_texture(size: int) -> Image.Image:
    """Crea textura de piedra procedural."""
    import random as stdlib_random
    img = Image.new("RGB", (size, size), _STONE_BG)
    draw = ImageDraw.Draw(img)
    rng = stdlib_random.Random(42)  # Seed fija para consistencia visual
    for _ in range(size * size // 8):
        x = rng.randint(0, size - 1)
        y = rng.randint(0, size - 1)
        variation = rng.randint(-15, 15)
        color = tuple(max(0, min(255, c + variation)) for c in _STONE_BG)
        draw.point((x, y), fill=color)
    return img


def render_rune(rune_id: str, size: int = 300) -> Image.Image:
    """Renderiza una runa del Elder Futhark sobre textura piedra.

    Wyrd (runa en blanco): círculo vacío.
    """
    img = _create_stone_texture(size)
    draw = ImageDraw.Draw(img)

    if rune_id == "wyrd":
        # Wyrd: círculo vacío (potencial puro)
        margin = int(size * 0.15)
        # Sombra
        draw.ellipse(
            [(margin + _SHADOW_OFFSET, margin + _SHADOW_OFFSET),
             (size - margin + _SHADOW_OFFSET, size - margin + _SHADOW_OFFSET)],
            outline=_SHADOW_COLOR, width=_SHADOW_WIDTH,
        )
        # Trazo principal
        draw.ellipse(
            [(margin, margin), (size - margin, size - margin)],
            outline=_STROKE_COLOR, width=_STROKE_WIDTH,
        )
        return img

    paths = RUNE_PATHS.get(rune_id)
    if not paths:
        logger.warning(f"Rune ID not found: {rune_id}")
        return img

    # Margen para que los trazos no toquen el borde
    margin = int(size * 0.10)
    draw_size = size - margin * 2

    for (x1, y1), (x2, y2) in paths:
        px1 = margin + x1 * draw_size
        py1 = margin + y1 * draw_size
        px2 = margin + x2 * draw_size
        py2 = margin + y2 * draw_size

        # Sombra (efecto tallado = profundidad)
        draw.line(
            [(px1 + _SHADOW_OFFSET, py1 + _SHADOW_OFFSET),
             (px2 + _SHADOW_OFFSET, py2 + _SHADOW_OFFSET)],
            fill=_SHADOW_COLOR, width=_SHADOW_WIDTH,
        )
        # Trazo principal
        draw.line(
            [(px1, py1), (px2, py2)],
            fill=_STROKE_COLOR, width=_STROKE_WIDTH,
        )

    return img


def render_rune_with_label(rune_id: str, label: str, size: int = 300) -> Image.Image:
    """Renderiza runa con etiqueta de texto debajo."""
    rune_img = render_rune(rune_id, size)
    label_h = 40
    canvas = Image.new("RGB", (size, size + label_h), color=(25, 20, 30))
    canvas.paste(rune_img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype(str(_FONT_PATH), size=18)
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    x = (size - text_w) // 2
    draw.text((x, size + 8), label, fill=(200, 185, 150), font=font)

    return canvas


def compose_runes(rune_images: list[Image.Image], labels: list[str] | None = None) -> BytesIO | None:
    """Compone múltiples runas en fila horizontal. Devuelve JPEG BytesIO."""
    try:
        if not rune_images:
            return None

        n = len(rune_images)
        rw, rh = rune_images[0].size
        gap = 20
        padding = 30

        canvas_w = n * rw + (n - 1) * gap + padding * 2
        canvas_h = rh + padding * 2

        canvas = Image.new("RGB", (canvas_w, canvas_h), color=(25, 20, 30))

        for i, img in enumerate(rune_images):
            x = padding + i * (rw + gap)
            canvas.paste(img, (x, padding))

        buf = BytesIO()
        canvas.convert("RGB").save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return buf

    except Exception as e:
        logger.error(f"Error composing runes: {e}")
        return None
