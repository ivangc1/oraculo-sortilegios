"""Generador de tiradas de tarot con SystemRandom (sin repetición)."""

import json
import random
from pathlib import Path

_rng = random.SystemRandom()

# Datos de cartas cargados al importar
_CARDS_DATA: dict | None = None
_ALL_CARDS: list[dict] | None = None


def _load_cards() -> None:
    global _CARDS_DATA, _ALL_CARDS
    if _CARDS_DATA is not None:
        return
    cards_path = Path(__file__).parent.parent / "data" / "tarot_cards.json"
    with open(cards_path, encoding="utf-8") as f:
        _CARDS_DATA = json.load(f)

    _ALL_CARDS = list(_CARDS_DATA["major"])
    for suit_cards in _CARDS_DATA["minor"].values():
        _ALL_CARDS.extend(suit_cards)


def get_all_cards() -> list[dict]:
    """Devuelve lista de las 78 cartas."""
    _load_cards()
    return _ALL_CARDS


def get_positions(variant: str) -> list[str]:
    """Devuelve las posiciones para una variante."""
    _load_cards()
    return _CARDS_DATA["positions"].get(variant, [])


def draw_cards(n: int, deck_size: int = 78) -> list[int]:
    """Tira n cartas sin repetición. Devuelve índices."""
    return _rng.sample(range(deck_size), n)


def draw_tarot(variant: str) -> list[dict]:
    """Tira completa: devuelve lista de cartas con posición e inversión.

    Returns:
        Lista de dicts con keys: id, name, file, inverted, position
    """
    _load_cards()

    count_map = {
        "1_carta": 1,
        "3_cartas": 3,
        "cruz_celta": 10,
    }
    n = count_map.get(variant, 1)
    positions = get_positions(variant)
    indices = draw_cards(n)

    result = []
    for i, card_idx in enumerate(indices):
        card = _ALL_CARDS[card_idx].copy()
        card["inverted"] = _rng.random() < 0.5
        card["position"] = positions[i] if i < len(positions) else None
        result.append(card)

    return result


def build_drawn_data(cards: list[dict]) -> dict:
    """Construye drawn_data JSON para usage_log."""
    return {
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
