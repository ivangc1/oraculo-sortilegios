"""Tests del generador de runas y renderer."""

from PIL import Image

from generators.runas import (
    build_drawn_data,
    draw_runes,
    get_all_runes,
    get_non_invertible,
    get_positions,
)
from images.rune_renderer import RUNE_PATHS, render_rune, render_rune_with_label, compose_runes


# === Datos ===

def test_25_runes_total():
    """24 Elder Futhark + Wyrd = 25."""
    runes = get_all_runes()
    assert len(runes) == 25


def test_rune_ids_unique():
    runes = get_all_runes()
    ids = [r["id"] for r in runes]
    assert len(ids) == len(set(ids))


def test_wyrd_included():
    runes = get_all_runes()
    ids = [r["id"] for r in runes]
    assert "wyrd" in ids


def test_non_invertible_set():
    """Runas simétricas no se invierten."""
    non_inv = get_non_invertible()
    # Las 9 del ROADMAP
    expected = {"gebo", "hagalaz", "isa", "jera", "eihwaz", "sowilo", "ingwaz", "dagaz", "wyrd"}
    assert non_inv == expected


# === Generador ===

def test_draw_odin_1_rune():
    result = draw_runes("odin")
    assert len(result) == 1
    assert result[0]["position"] == "Runa de Odín"


def test_draw_nornas_3_runes():
    result = draw_runes("nornas")
    assert len(result) == 3
    positions = [r["position"] for r in result]
    assert "Urd (Pasado)" in positions
    assert "Verdandi (Presente)" in positions
    assert "Skuld (Futuro)" in positions


def test_draw_cruz_5_runes():
    result = draw_runes("cruz")
    assert len(result) == 5
    assert result[0]["position"] == "Centro (Presente)"


def test_no_duplicate_runes():
    for _ in range(50):
        runes = draw_runes("cruz")
        ids = [r["id"] for r in runes]
        assert len(ids) == len(set(ids))


def test_non_invertible_never_inverted():
    """Runas simétricas nunca salen invertidas."""
    non_inv = get_non_invertible()
    for _ in range(100):
        runes = draw_runes("cruz")
        for r in runes:
            if r["id"] in non_inv:
                assert r["inverted"] is False, f"{r['id']} salió invertida"


def test_invertible_sometimes_inverted():
    """Runas no simétricas salen invertidas al menos a veces."""
    inversions = set()
    for _ in range(100):
        runes = draw_runes("cruz")
        for r in runes:
            if r["id"] not in get_non_invertible():
                inversions.add(r["inverted"])
    assert True in inversions and False in inversions


def test_drawn_data_structure():
    runes = draw_runes("nornas")
    data = build_drawn_data(runes)
    assert "runes" in data
    assert len(data["runes"]) == 3
    for r in data["runes"]:
        assert set(r.keys()) == {"id", "name", "inverted", "position"}


# === RUNE_PATHS (trazos vectoriales) ===

def test_all_24_runes_have_paths():
    """Cada runa del Elder Futhark tiene definición de trazos."""
    runes = get_all_runes()
    for rune in runes:
        if rune["id"] == "wyrd":
            continue  # Wyrd es círculo vacío, no paths
        assert rune["id"] in RUNE_PATHS, f"Falta RUNE_PATHS para {rune['id']}"


def test_rune_paths_have_segments():
    """Cada runa tiene al menos 1 segmento."""
    for rune_id, paths in RUNE_PATHS.items():
        assert len(paths) >= 1, f"{rune_id} sin segmentos"


def test_rune_paths_coordinates_normalized():
    """Coordenadas entre 0 y 1."""
    for rune_id, paths in RUNE_PATHS.items():
        for (x1, y1), (x2, y2) in paths:
            assert 0.0 <= x1 <= 1.0, f"{rune_id}: x1={x1} fuera de rango"
            assert 0.0 <= y1 <= 1.0, f"{rune_id}: y1={y1} fuera de rango"
            assert 0.0 <= x2 <= 1.0, f"{rune_id}: x2={x2} fuera de rango"
            assert 0.0 <= y2 <= 1.0, f"{rune_id}: y2={y2} fuera de rango"


def test_rune_paths_no_zero_length():
    """No hay segmentos de longitud cero (punto → punto)."""
    for rune_id, paths in RUNE_PATHS.items():
        for (x1, y1), (x2, y2) in paths:
            assert (x1, y1) != (x2, y2), f"{rune_id}: segmento de longitud cero"


# === Renderer ===

def test_render_each_rune():
    """Cada runa renderiza correctamente."""
    runes = get_all_runes()
    for rune in runes:
        img = render_rune(rune["id"])
        assert isinstance(img, Image.Image)
        assert img.size == (300, 300)


def test_render_wyrd():
    """Wyrd renderiza (círculo vacío)."""
    img = render_rune("wyrd")
    assert isinstance(img, Image.Image)


def test_render_with_label():
    img = render_rune_with_label("fehu", "Fehu — Pasado")
    assert isinstance(img, Image.Image)
    assert img.size[1] == 340  # 300 + 40 label


def test_compose_runes_produces_jpeg():
    images = [render_rune_with_label(rid, rid) for rid in ("fehu", "uruz", "thurisaz")]
    buf = compose_runes(images)
    assert buf is not None
    img = Image.open(buf)
    assert img.format == "JPEG"
    buf.close()


def test_compose_single_rune():
    images = [render_rune_with_label("ansuz", "Runa de Odín")]
    buf = compose_runes(images)
    assert buf is not None
    buf.close()
