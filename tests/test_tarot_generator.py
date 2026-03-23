"""Tests del generador de tarot: unicidad, sin repetición, drawn_data."""

from generators.tarot import (
    build_drawn_data,
    draw_cards,
    draw_tarot,
    get_all_cards,
    get_positions,
)


def test_deck_has_78_cards():
    """El mazo tiene exactamente 78 cartas."""
    cards = get_all_cards()
    assert len(cards) == 78


def test_deck_ids_unique():
    """Todos los IDs son únicos."""
    cards = get_all_cards()
    ids = [c["id"] for c in cards]
    assert len(ids) == len(set(ids))


def test_deck_names_unique():
    """Todos los nombres son únicos."""
    cards = get_all_cards()
    names = [c["name"] for c in cards]
    assert len(names) == len(set(names))


def test_nomenclature_hierofante():
    """Nomenclatura Tam: Hierofante, no Sumo Sacerdote."""
    cards = get_all_cards()
    names = [c["name"] for c in cards]
    assert "El Hierofante" in names
    assert "El Sumo Sacerdote" not in names


def test_nomenclature_bastos():
    """Nomenclatura Tam: Bastos, no Varas."""
    cards = get_all_cards()
    names = [c["name"] for c in cards]
    bastos = [n for n in names if "Bastos" in n]
    varas = [n for n in names if "Varas" in n]
    assert len(bastos) == 14
    assert len(varas) == 0


def test_nomenclature_sota():
    """Nomenclatura Tam: Sota, no Paje."""
    cards = get_all_cards()
    names = [c["name"] for c in cards]
    sotas = [n for n in names if "Sota" in n]
    pajes = [n for n in names if "Paje" in n]
    assert len(sotas) == 4
    assert len(pajes) == 0


def test_nomenclature_caballero():
    """Nomenclatura Tam: Caballero, no Caballo."""
    cards = get_all_cards()
    names = [c["name"] for c in cards]
    caballeros = [n for n in names if "Caballero" in n]
    caballos = [n for n in names if "Caballo" in n]
    assert len(caballeros) == 4
    assert len(caballos) == 0


def test_draw_cards_no_repetition():
    """draw_cards nunca repite índices."""
    for _ in range(100):
        indices = draw_cards(10)
        assert len(indices) == len(set(indices))


def test_draw_cards_in_range():
    """Índices siempre dentro del rango del mazo."""
    for _ in range(100):
        indices = draw_cards(10, deck_size=78)
        for idx in indices:
            assert 0 <= idx < 78


def test_draw_tarot_1_carta():
    """Tirada de 1 carta devuelve exactamente 1 carta con posición."""
    cards = draw_tarot("1_carta")
    assert len(cards) == 1
    assert "id" in cards[0]
    assert "name" in cards[0]
    assert "inverted" in cards[0]
    assert isinstance(cards[0]["inverted"], bool)


def test_draw_tarot_3_cartas():
    """Tirada de 3 cartas devuelve 3 con posiciones correctas."""
    cards = draw_tarot("3_cartas")
    assert len(cards) == 3
    positions = [c["position"] for c in cards]
    assert positions == ["Pasado", "Presente", "Futuro"]


def test_draw_tarot_cruz_celta():
    """Cruz Celta devuelve 10 cartas con posiciones correctas."""
    cards = draw_tarot("cruz_celta")
    assert len(cards) == 10
    assert cards[0]["position"] == "Situación presente"
    assert cards[1]["position"] == "Obstáculo"
    assert cards[9]["position"] == "Resultado final"


def test_draw_tarot_no_duplicate_cards():
    """Nunca salen cartas repetidas en una tirada."""
    for _ in range(50):
        cards = draw_tarot("cruz_celta")
        ids = [c["id"] for c in cards]
        assert len(ids) == len(set(ids))


def test_draw_tarot_inversions_vary():
    """Las inversiones no son constantes (al menos alguna invertida en 50 tiradas)."""
    inversions = set()
    for _ in range(50):
        cards = draw_tarot("cruz_celta")
        for c in cards:
            inversions.add(c["inverted"])
    assert True in inversions and False in inversions


def test_positions_1_carta():
    assert get_positions("1_carta") == ["Carta"]


def test_positions_3_cartas():
    assert get_positions("3_cartas") == ["Pasado", "Presente", "Futuro"]


def test_positions_cruz_celta():
    positions = get_positions("cruz_celta")
    assert len(positions) == 10
    assert positions[0] == "Situación presente"


def test_build_drawn_data():
    """drawn_data JSON tiene estructura correcta."""
    cards = draw_tarot("3_cartas")
    data = build_drawn_data(cards)
    assert "cards" in data
    assert len(data["cards"]) == 3
    for c in data["cards"]:
        assert "id" in c
        assert "name" in c
        assert "inverted" in c
        assert "position" in c


def test_build_drawn_data_fields():
    """drawn_data contiene solo los campos esperados."""
    cards = [{"id": "major_00", "name": "El Loco", "inverted": True, "position": "Pasado", "file": "major_00.png"}]
    data = build_drawn_data(cards)
    card_data = data["cards"][0]
    assert set(card_data.keys()) == {"id", "name", "inverted", "position"}
    assert "file" not in card_data  # file no se guarda en drawn_data
