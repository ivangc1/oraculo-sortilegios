"""Tests de composiciones de tarot e imágenes."""

from io import BytesIO

from PIL import Image

from generators.tarot import draw_tarot
from images.card_cache import clear_cache, load_card_image, invert_card_image
from images.tarot_composer import (
    build_caption,
    build_text_fallback,
    compose_celtic_cross,
    compose_single,
    compose_tarot,
    compose_three,
    compose_to_jpeg,
)


def test_load_card_placeholder():
    """Sin PNGs reales, genera placeholder."""
    clear_cache()
    img = load_card_image("major_00")
    assert isinstance(img, Image.Image)
    assert img.size[0] > 0 and img.size[1] > 0


def test_invert_card():
    """Invertir carta produce imagen del mismo tamaño."""
    clear_cache()
    original = load_card_image("major_01")
    inverted = invert_card_image(original)
    assert inverted.size == original.size


def test_compose_to_jpeg_produces_valid():
    """compose_to_jpeg produce un JPEG válido en BytesIO."""
    img = Image.new("RGB", (300, 500), color=(100, 50, 50))
    buf = compose_to_jpeg(img)
    assert isinstance(buf, BytesIO)
    assert buf.tell() == 0  # seek(0) ya aplicado
    # Verificar que es JPEG válido
    loaded = Image.open(buf)
    assert loaded.format == "JPEG"
    buf.close()


def test_compose_to_jpeg_under_10mb():
    """Composición grande sigue estando bajo 10MB."""
    # Crear imagen grande para probar
    img = Image.new("RGB", (5000, 5000), color=(100, 50, 50))
    buf = compose_to_jpeg(img)
    size_mb = buf.getbuffer().nbytes / (1024 * 1024)
    assert size_mb < 10.0
    buf.close()


def test_compose_single():
    """Composición de 1 carta produce JPEG."""
    clear_cache()
    cards = draw_tarot("1_carta")
    buf = compose_single(cards)
    assert buf is not None
    img = Image.open(buf)
    assert img.format == "JPEG"
    buf.close()


def test_compose_three():
    """Composición de 3 cartas produce JPEG."""
    clear_cache()
    cards = draw_tarot("3_cartas")
    buf = compose_three(cards)
    assert buf is not None
    img = Image.open(buf)
    assert img.format == "JPEG"
    buf.close()


def test_compose_celtic_cross():
    """Composición Cruz Celta (10 cartas) produce JPEG."""
    clear_cache()
    cards = draw_tarot("cruz_celta")
    buf = compose_celtic_cross(cards)
    assert buf is not None
    img = Image.open(buf)
    assert img.format == "JPEG"
    size_mb = buf.getbuffer().nbytes / (1024 * 1024)
    assert size_mb < 10.0, f"Cruz Celta demasiado grande: {size_mb:.1f}MB"
    buf.close()


def test_compose_celtic_cross_too_few_cards():
    """Cruz Celta con <10 cartas devuelve None."""
    clear_cache()
    cards = draw_tarot("3_cartas")  # Solo 3
    buf = compose_celtic_cross(cards)
    assert buf is None


def test_compose_tarot_dispatcher():
    """compose_tarot despacha correctamente por variante."""
    clear_cache()
    for variant in ("1_carta", "3_cartas", "cruz_celta"):
        cards = draw_tarot(variant)
        buf = compose_tarot(variant, cards)
        assert buf is not None, f"compose_tarot devolvió None para {variant}"
        buf.close()


def test_build_caption_3_cartas():
    """Caption de 3 cartas incluye posiciones y nombres."""
    cards = [
        {"id": "major_00", "name": "El Loco", "inverted": False, "position": "Pasado"},
        {"id": "major_01", "name": "El Mago", "inverted": True, "position": "Presente"},
        {"id": "major_02", "name": "La Sacerdotisa", "inverted": False, "position": "Futuro"},
    ]
    caption = build_caption("3_cartas", cards)
    assert "Pasado: El Loco" in caption
    assert "Presente: El Mago (invertida)" in caption
    assert "Futuro: La Sacerdotisa" in caption


def test_build_text_fallback():
    """Fallback texto descriptivo cuando falla composición."""
    cards = [{"id": "major_00", "name": "El Loco", "inverted": True, "position": "Carta"}]
    text = build_text_fallback("1_carta", cards)
    assert "El Loco" in text
    assert "↓" in text
    assert "🃏" in text
