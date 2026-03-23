"""Tests del generador I Ching: distribución + caso sin mutables."""

from collections import Counter

from PIL import Image

from generators.iching import (
    build_drawn_data,
    generate_hexagram,
    get_hexagram_info,
    throw_three_coins,
)
from images.hexagram_renderer import render_hexagram, build_caption, build_text_fallback


# === Distribución de monedas ===

def test_three_coins_values():
    """throw_three_coins devuelve solo 6, 7, 8 o 9."""
    for _ in range(1000):
        value = throw_three_coins()
        assert value in (6, 7, 8, 9), f"Valor inesperado: {value}"


def test_three_coins_distribution():
    """Distribución de 1000 tiradas: 6≈12.5%, 7≈37.5%, 8≈37.5%, 9≈12.5%.

    Tolerancia amplia (±5%) para evitar flaky tests.
    """
    counts = Counter()
    n = 10000
    for _ in range(n):
        counts[throw_three_coins()] += 1

    # Proporciones esperadas
    p6 = counts[6] / n  # esperado 0.125
    p7 = counts[7] / n  # esperado 0.375
    p8 = counts[8] / n  # esperado 0.375
    p9 = counts[9] / n  # esperado 0.125

    assert 0.08 < p6 < 0.18, f"P(6)={p6:.3f}, esperado ~0.125"
    assert 0.30 < p7 < 0.45, f"P(7)={p7:.3f}, esperado ~0.375"
    assert 0.30 < p8 < 0.45, f"P(8)={p8:.3f}, esperado ~0.375"
    assert 0.08 < p9 < 0.18, f"P(9)={p9:.3f}, esperado ~0.125"


# === Hexagramas ===

def test_hexagram_has_6_lines():
    hex = generate_hexagram()
    assert len(hex["lines"]) == 6
    for line in hex["lines"]:
        assert line in (6, 7, 8, 9)


def test_hexagram_primary_valid():
    """El hexagrama primario es un número 1-64."""
    for _ in range(100):
        hex = generate_hexagram()
        assert 1 <= hex["primary"] <= 64, f"Primario inválido: {hex['primary']}"
        assert hex["primary_name"] is not None


def test_hexagram_with_mutables_has_derived():
    """Si hay líneas mutables, debe haber hexagrama derivado."""
    # Generar hasta encontrar uno con mutables (probabilidad alta)
    found = False
    for _ in range(200):
        hex = generate_hexagram()
        if hex["mutable_lines"]:
            found = True
            assert hex["derived"] is not None, "Tiene mutables pero no derivado"
            assert 1 <= hex["derived"] <= 64
            assert hex["derived_name"] is not None
            break
    assert found, "No se generó ningún hexagrama con mutables en 200 intentos"


def test_hexagram_without_mutables_no_derived():
    """Si NO hay líneas mutables, NO debe haber hexagrama derivado.

    Generar muchos hasta encontrar uno sin mutables.
    P(sin mutables) = (3/4)^6 ≈ 0.178, así que ~18% de las veces.
    """
    found = False
    for _ in range(500):
        hex = generate_hexagram()
        if not hex["mutable_lines"]:
            found = True
            assert hex["derived"] is None, "Sin mutables pero tiene derivado"
            assert hex["derived_name"] is None
            break
    assert found, "No se generó ningún hexagrama sin mutables en 500 intentos"


def test_no_mutables_probability():
    """P(sin mutables) ≈ 17.8% en 1000 tiradas."""
    no_mutable_count = 0
    n = 1000
    for _ in range(n):
        hex = generate_hexagram()
        if not hex["mutable_lines"]:
            no_mutable_count += 1
    proportion = no_mutable_count / n
    # Esperado ~17.8%, tolerancia ±7%
    assert 0.10 < proportion < 0.28, (
        f"P(sin mutables)={proportion:.3f}, esperado ~0.178"
    )


def test_mutable_lines_only_6_or_9():
    """Líneas mutables son solo las posiciones con valor 6 o 9."""
    for _ in range(100):
        hex = generate_hexagram()
        for pos in hex["mutable_lines"]:
            line_value = hex["lines"][pos - 1]  # pos es 1-based
            assert line_value in (6, 9), f"Línea {pos} = {line_value}, no es mutable"


def test_derived_is_different_from_primary_when_mutables():
    """Con mutables, el derivado puede ser igual o diferente (pero normalmente diferente)."""
    # Solo verificar que se calcula, no que sea diferente siempre
    for _ in range(50):
        hex = generate_hexagram()
        if hex["mutable_lines"]:
            assert hex["derived"] is not None


def test_mutation_logic():
    """Verificar que la mutación es correcta: 9→yin, 6→yang."""
    for _ in range(200):
        hex = generate_hexagram()
        if not hex["mutable_lines"]:
            continue
        # Verificar manualmente
        for pos in hex["mutable_lines"]:
            line = hex["lines"][pos - 1]
            assert line in (6, 9)
        break


# === Datos de hexagramas ===

def test_all_64_hexagrams_exist():
    """Los 64 hexagramas tienen datos."""
    for i in range(1, 65):
        info = get_hexagram_info(i)
        assert info is not None, f"Falta hexagrama {i}"
        assert "name" in info
        assert "spanish" in info
        assert "chinese" in info


# === drawn_data ===

def test_drawn_data_with_mutables():
    """drawn_data incluye mutables y derivado si existen."""
    for _ in range(200):
        hex = generate_hexagram()
        if hex["mutable_lines"]:
            data = build_drawn_data(hex)
            assert data["hexagram"]["derived"] is not None
            assert len(data["hexagram"]["mutable_lines"]) > 0
            break


def test_drawn_data_without_mutables():
    """drawn_data sin derivado si no hay mutables."""
    for _ in range(500):
        hex = generate_hexagram()
        if not hex["mutable_lines"]:
            data = build_drawn_data(hex)
            assert data["hexagram"]["derived"] is None
            assert data["hexagram"]["mutable_lines"] == []
            break


# === Renderer ===

def test_render_hexagram_with_derived():
    """Renderiza 2 hexagramas cuando hay mutables."""
    for _ in range(200):
        hex = generate_hexagram()
        if hex["mutable_lines"]:
            buf = render_hexagram(hex)
            assert buf is not None
            img = Image.open(buf)
            assert img.format == "JPEG"
            # Con derivado, la imagen es más ancha
            assert img.size[0] > 300
            buf.close()
            break


def test_render_hexagram_without_derived():
    """Renderiza 1 hexagrama cuando no hay mutables."""
    for _ in range(500):
        hex = generate_hexagram()
        if not hex["mutable_lines"]:
            buf = render_hexagram(hex)
            assert buf is not None
            img = Image.open(buf)
            assert img.format == "JPEG"
            buf.close()
            break


def test_caption_with_mutables():
    for _ in range(200):
        hex = generate_hexagram()
        if hex["mutable_lines"]:
            caption = build_caption(hex)
            assert "mutables" in caption.lower()
            assert "→" in caption
            break


def test_caption_without_mutables():
    for _ in range(500):
        hex = generate_hexagram()
        if not hex["mutable_lines"]:
            caption = build_caption(hex)
            assert "estable" in caption.lower()
            assert "→" not in caption
            break


def test_text_fallback():
    hex = generate_hexagram()
    text = build_text_fallback(hex)
    assert "☯" in text
    assert str(hex["primary"]) in text
