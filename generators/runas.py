"""Generador de tiradas de runas con SystemRandom."""

import json
import random
from pathlib import Path

_rng = random.SystemRandom()

_RUNES_DATA: dict | None = None
_ALL_RUNES: list[dict] | None = None
_NON_INVERTIBLE: set[str] | None = None


def _load_runes() -> None:
    global _RUNES_DATA, _ALL_RUNES, _NON_INVERTIBLE
    if _RUNES_DATA is not None:
        return
    runes_path = Path(__file__).parent.parent / "data" / "runas.json"
    with open(runes_path, encoding="utf-8") as f:
        _RUNES_DATA = json.load(f)
    _ALL_RUNES = _RUNES_DATA["runes"]
    _NON_INVERTIBLE = set(_RUNES_DATA["non_invertible"])


def get_all_runes() -> list[dict]:
    _load_runes()
    return _ALL_RUNES


def get_positions(variant: str) -> list[str]:
    _load_runes()
    return _RUNES_DATA["positions"].get(variant, [])


def get_non_invertible() -> set[str]:
    _load_runes()
    return _NON_INVERTIBLE


def draw_runes(variant: str) -> list[dict]:
    """Tira de runas según variante. Devuelve lista con id, name, inverted, position."""
    _load_runes()

    count_map = {
        "odin": 1,
        "nornas": 3,
        "cruz": 5,
    }
    n = count_map.get(variant, 1)
    positions = get_positions(variant)

    # Incluye Wyrd (25 runas total)
    indices = _rng.sample(range(len(_ALL_RUNES)), n)

    result = []
    for i, idx in enumerate(indices):
        rune = _ALL_RUNES[idx].copy()
        # Solo invertir si la runa lo permite
        if rune["id"] in _NON_INVERTIBLE:
            rune["inverted"] = False
        else:
            rune["inverted"] = _rng.random() < 0.5
        rune["position"] = positions[i] if i < len(positions) else None
        result.append(rune)

    return result


def build_drawn_data(runes: list[dict]) -> dict:
    """Construye drawn_data JSON para usage_log."""
    return {
        "runes": [
            {
                "id": r["id"],
                "name": r["name"],
                "inverted": r["inverted"],
                "position": r.get("position"),
            }
            for r in runes
        ]
    }
