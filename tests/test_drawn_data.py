"""Tests de drawn_data JSON schema para TODOS los modos.

Verifica que cada modo genera drawn_data con la estructura correcta
según sección 12.5 del ROADMAP.
"""

from generators.tarot import build_drawn_data as tarot_drawn, draw_tarot
from generators.runas import build_drawn_data as runas_drawn, draw_runes
from generators.iching import build_drawn_data as iching_drawn, generate_hexagram
from generators.geomancia import (
    build_drawn_data_single as geo_drawn_single,
    build_drawn_data_shield as geo_drawn_shield,
    generate_figure, generate_shield,
)
from service.calculators.numerologia import full_report, compatibility


# === Tarot ===

def test_tarot_drawn_data_1_carta():
    cards = draw_tarot("1_carta")
    data = tarot_drawn(cards)
    assert "cards" in data
    assert len(data["cards"]) == 1
    c = data["cards"][0]
    assert set(c.keys()) == {"id", "name", "inverted", "position"}
    assert isinstance(c["id"], str)
    assert isinstance(c["name"], str)
    assert isinstance(c["inverted"], bool)


def test_tarot_drawn_data_3_cartas():
    cards = draw_tarot("3_cartas")
    data = tarot_drawn(cards)
    assert len(data["cards"]) == 3
    positions = [c["position"] for c in data["cards"]]
    assert positions == ["Pasado", "Presente", "Futuro"]


def test_tarot_drawn_data_cruz_celta():
    cards = draw_tarot("cruz_celta")
    data = tarot_drawn(cards)
    assert len(data["cards"]) == 10
    assert data["cards"][0]["position"] == "Situación presente"
    assert data["cards"][9]["position"] == "Resultado final"


def test_tarot_drawn_data_no_file_field():
    """drawn_data no incluye campo 'file' (solo datos relevantes)."""
    cards = draw_tarot("1_carta")
    data = tarot_drawn(cards)
    for c in data["cards"]:
        assert "file" not in c


# === Runas ===

def test_runas_drawn_data_odin():
    runes = draw_runes("odin")
    data = runas_drawn(runes)
    assert "runes" in data
    assert len(data["runes"]) == 1
    r = data["runes"][0]
    assert set(r.keys()) == {"id", "name", "inverted", "position"}


def test_runas_drawn_data_nornas():
    runes = draw_runes("nornas")
    data = runas_drawn(runes)
    assert len(data["runes"]) == 3


def test_runas_drawn_data_cruz():
    runes = draw_runes("cruz")
    data = runas_drawn(runes)
    assert len(data["runes"]) == 5


# === I Ching ===

def test_iching_drawn_data_with_mutables():
    for _ in range(200):
        h = generate_hexagram()
        if h["mutable_lines"]:
            data = iching_drawn(h)
            hx = data["hexagram"]
            assert "lines" in hx
            assert len(hx["lines"]) == 6
            assert "primary" in hx
            assert "primary_name" in hx
            assert "derived" in hx
            assert hx["derived"] is not None
            assert "mutable_lines" in hx
            assert len(hx["mutable_lines"]) > 0
            break


def test_iching_drawn_data_without_mutables():
    for _ in range(500):
        h = generate_hexagram()
        if not h["mutable_lines"]:
            data = iching_drawn(h)
            hx = data["hexagram"]
            assert hx["derived"] is None
            assert hx["derived_name"] is None
            assert hx["mutable_lines"] == []
            break


# === Geomancia ===

def test_geomancia_drawn_data_single():
    fig = generate_figure()
    data = geo_drawn_single(fig)
    assert "figures" in data
    assert len(data["figures"]) == 1
    f = data["figures"][0]
    assert "name" in f
    assert "points" in f
    assert len(f["points"]) == 4
    assert "position" in f


def test_geomancia_drawn_data_shield():
    shield = generate_shield()
    data = geo_drawn_shield(shield)
    assert "figures" in data
    # 4 madres + 4 hijas + 4 sobrinas + 2 testigos + juez + reconciliador = 16
    assert len(data["figures"]) == 16
    positions = [f["position"] for f in data["figures"]]
    assert "Juez" in positions
    assert "Reconciliador" in positions
    assert "Madre 1" in positions
    assert "Hija 1" in positions


# === Numerología ===

def test_numerologia_drawn_data_informe():
    report = full_report("15/06/1993", full_name="Juan García")
    assert "life_path" in report
    assert "personal_year" in report
    assert "personal_month" in report
    assert "expression" in report
    assert "soul" in report
    assert "personality" in report
    assert isinstance(report["life_path"], int)


def test_numerologia_drawn_data_informe_without_name():
    report = full_report("15/06/1993")
    assert "life_path" in report
    assert "expression" not in report


def test_numerologia_drawn_data_compatibilidad():
    data = compatibility("15/06/1993", "25/12/1990")
    assert "life_path_1" in data
    assert "life_path_2" in data
    assert isinstance(data["life_path_1"], int)
    assert isinstance(data["life_path_2"], int)


# === Oráculo ===

def test_oraculo_drawn_data():
    """Oráculo: drawn_data solo tiene question_length (privacidad)."""
    data = {"question_length": 87}
    assert "question_length" in data
    assert isinstance(data["question_length"], int)
    # NO debe contener la pregunta completa
    assert "question" not in data or data.get("question") is None
