"""Generador de tiradas de tarot con SystemRandom (sin repetición).

Soporte multi-mazo: rws (Rider-Waite-Smith), marsella (Tarot de Marsella).
"""

import json
import random
from pathlib import Path

_rng = random.SystemRandom()

# Datos de cartas cargados por mazo — {deck_id: {"data": dict, "all_cards": list}}
_DECKS: dict[str, dict] = {}

# Mazos disponibles: deck_id -> (json_filename, label)
AVAILABLE_DECKS = {
    "rws": ("tarot_cards.json", "Rider-Waite-Smith"),
    "marsella": ("tarot_marsella.json", "Tarot de Marsella"),
}


def _load_deck(deck: str = "rws") -> None:
    if deck in _DECKS:
        return
    if deck not in AVAILABLE_DECKS:
        raise ValueError(f"Mazo desconocido: {deck}")

    filename = AVAILABLE_DECKS[deck][0]
    cards_path = Path(__file__).parent.parent / "data" / filename
    with open(cards_path, encoding="utf-8") as f:
        data = json.load(f)

    all_cards = list(data["major"])
    for suit_cards in data["minor"].values():
        all_cards.extend(suit_cards)

    _DECKS[deck] = {"data": data, "all_cards": all_cards}


def get_all_cards(deck: str = "rws") -> list[dict]:
    """Devuelve lista de las 78 cartas del mazo indicado."""
    _load_deck(deck)
    return _DECKS[deck]["all_cards"]


def get_positions(variant: str, deck: str = "rws") -> list[str]:
    """Devuelve las posiciones para una variante."""
    _load_deck(deck)
    return _DECKS[deck]["data"]["positions"].get(variant, [])


def draw_cards(n: int, deck_size: int = 78) -> list[int]:
    """Tira n cartas sin repetición. Devuelve índices."""
    return _rng.sample(range(deck_size), n)


def draw_tarot(variant: str, deck: str = "rws") -> list[dict]:
    """Tira completa: devuelve lista de cartas con posición e inversión.

    Args:
        variant: tipo de tirada (1_carta, 3_cartas, cruz_celta, etc.)
        deck: mazo a usar (rws, marsella)

    Returns:
        Lista de dicts con keys: id, name, file, inverted, position, deck
    """
    _load_deck(deck)

    count_map = {
        "1_carta": 1,
        "3_cartas": 3,
        "cruz_celta": 10,
        "herradura": 7,
        "relacion": 6,
        "estrella": 7,
        "cruz_simple": 5,
        "si_no": 3,
        "tirada_dia": 1,
    }
    n = count_map.get(variant, 1)
    positions = get_positions(variant, deck)
    all_cards = _DECKS[deck]["all_cards"]
    indices = draw_cards(n, len(all_cards))

    result = []
    for i, card_idx in enumerate(indices):
        card = all_cards[card_idx].copy()
        card["inverted"] = _rng.random() < 0.5
        card["position"] = positions[i] if i < len(positions) else None
        card["deck"] = deck
        result.append(card)

    return result


def build_drawn_data(cards: list[dict]) -> dict:
    """Construye drawn_data JSON para usage_log."""
    return {
        "deck": cards[0].get("deck", "rws") if cards else "rws",
        "cards": [
            {
                "id": c["id"],
                "name": c["name"],
                "inverted": c["inverted"],
                "position": c.get("position"),
            }
            for c in cards
        ]
    }


def get_deck_label(deck: str) -> str:
    """Nombre legible del mazo."""
    return AVAILABLE_DECKS.get(deck, ("", deck))[1]
