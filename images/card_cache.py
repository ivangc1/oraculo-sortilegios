"""LRU cache de imágenes de cartas con EXIF transpose.

El with cierra el file handle, copy() mantiene datos en RAM.
exif_transpose() normaliza orientación EXIF antes de cachear.
Concurrencia: lru_cache es seguro en asyncio single-thread.
"""

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageOps

TAROT_ASSETS_DIR = Path(__file__).parent.parent / "assets" / "tarot"


@lru_cache(maxsize=78)
def load_card_image(card_id: str) -> Image.Image:
    """Carga y cachea una imagen de carta. EXIF normalizado."""
    filepath = TAROT_ASSETS_DIR / f"{card_id}.png"
    if not filepath.exists():
        return _create_placeholder(card_id)
    with Image.open(filepath) as img:
        img = ImageOps.exif_transpose(img)
        return img.copy()


def _create_placeholder(card_id: str) -> Image.Image:
    """Crea placeholder si falta el PNG (desarrollo)."""
    from PIL import ImageDraw, ImageFont

    img = Image.new("RGB", (300, 500), color=(40, 30, 50))
    draw = ImageDraw.Draw(img)

    # Borde
    draw.rectangle([(5, 5), (294, 494)], outline=(180, 160, 120), width=3)

    # Texto con nombre de carta
    try:
        font = ImageFont.truetype(
            str(Path(__file__).parent.parent / "assets" / "fonts" / "NotoSans-Regular.ttf"),
            size=18,
        )
    except (OSError, IOError):
        font = ImageFont.load_default()

    # ID legible
    display = card_id.replace("_", " ").title()
    # Centrar texto
    bbox = draw.textbbox((0, 0), display, font=font)
    text_w = bbox[2] - bbox[0]
    x = (300 - text_w) // 2
    draw.text((x, 230), display, fill=(180, 160, 120), font=font)

    return img


def invert_card_image(img: Image.Image) -> Image.Image:
    """Rota 180 grados para carta invertida."""
    return img.rotate(180, expand=False)


def clear_cache() -> None:
    """Limpia el cache (para tests)."""
    load_card_image.cache_clear()
