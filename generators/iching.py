"""Generador de hexagramas I Ching con método de 3 monedas.

Distribución de probabilidades por línea (3 monedas, cara=3, cruz=2):
  6 (yin viejo, mutable)  = 1/8 = 12.5%  → sum=6
  7 (yang joven)          = 3/8 = 37.5%  → sum=7
  8 (yin joven)           = 3/8 = 37.5%  → sum=8
  9 (yang viejo, mutable) = 1/8 = 12.5%  → sum=9

Si NO hay líneas mutables → no hay hexagrama derivado.
"""

import json
import random
from pathlib import Path

_rng = random.SystemRandom()

_HEXAGRAM_DATA: dict | None = None
_TRIGRAM_LOOKUP: dict[str, str] | None = None

# Tabla King Wen: (trigrama_superior, trigrama_inferior) → número de hexagrama
# Trigramas codificados como cadena de bits: 1=yang, 0=yin
_KING_WEN_TABLE: dict[tuple[str, str], int] = {
    ("111", "111"): 1,  ("000", "000"): 2,  ("010", "001"): 3,  ("100", "010"): 4,
    ("010", "111"): 5,  ("111", "010"): 6,  ("000", "010"): 7,  ("010", "000"): 8,
    ("110", "111"): 9,  ("111", "011"): 10, ("000", "111"): 11, ("111", "000"): 12,
    ("111", "101"): 13, ("101", "111"): 14, ("000", "100"): 15, ("001", "000"): 16,
    ("011", "001"): 17, ("100", "110"): 18, ("000", "011"): 19, ("110", "000"): 20,
    ("101", "001"): 21, ("100", "101"): 22, ("100", "000"): 23, ("000", "001"): 24,
    ("111", "001"): 25, ("100", "111"): 26, ("100", "001"): 27, ("011", "110"): 28,
    ("010", "010"): 29, ("101", "101"): 30, ("011", "100"): 31, ("001", "110"): 32,
    ("111", "100"): 33, ("001", "111"): 34, ("101", "000"): 35, ("000", "101"): 36,
    ("110", "101"): 37, ("101", "011"): 38, ("010", "100"): 39, ("001", "010"): 40,
    ("100", "011"): 41, ("110", "001"): 42, ("011", "111"): 43, ("111", "110"): 44,
    ("011", "000"): 45, ("000", "110"): 46, ("011", "010"): 47, ("010", "110"): 48,
    ("011", "101"): 49, ("101", "110"): 50, ("001", "001"): 51, ("100", "100"): 52,
    ("110", "100"): 53, ("001", "011"): 54, ("001", "101"): 55, ("101", "100"): 56,
    ("110", "110"): 57, ("011", "011"): 58, ("110", "010"): 59, ("010", "011"): 60,
    ("110", "011"): 61, ("001", "100"): 62, ("010", "101"): 63, ("101", "010"): 64,
}


def _load_hexagrams() -> None:
    global _HEXAGRAM_DATA, _TRIGRAM_LOOKUP
    if _HEXAGRAM_DATA is not None:
        return
    path = Path(__file__).parent.parent / "data" / "iching_hexagrams.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _HEXAGRAM_DATA = data["hexagrams"]
    _TRIGRAM_LOOKUP = data["trigram_lookup"]


def get_hexagram_info(number: int) -> dict | None:
    """Devuelve info de un hexagrama por número (1-64)."""
    _load_hexagrams()
    return _HEXAGRAM_DATA.get(str(number))


def throw_three_coins() -> int:
    """Tira 3 monedas. Cara=3, Cruz=2. Devuelve suma (6, 7, 8, o 9)."""
    return sum(_rng.choice([2, 3]) for _ in range(3))


def generate_hexagram() -> dict:
    """Genera un hexagrama completo con el método de 3 monedas.

    Returns:
        dict con:
        - lines: lista de 6 valores (6,7,8,9), de abajo arriba
        - primary: número del hexagrama primario
        - primary_name: nombre del hexagrama primario
        - derived: número del derivado (None si sin mutables)
        - derived_name: nombre del derivado (None si sin mutables)
        - mutable_lines: lista de posiciones (1-6) con líneas mutables
    """
    _load_hexagrams()

    # Generar 6 líneas (de abajo arriba)
    lines = [throw_three_coins() for _ in range(6)]

    # Determinar líneas mutables
    mutable_lines = [i + 1 for i, line in enumerate(lines) if line in (6, 9)]

    # Convertir a bits para buscar hexagrama
    # 6=yin viejo (0), 7=yang joven (1), 8=yin joven (0), 9=yang viejo (1)
    primary_bits = [1 if line in (7, 9) else 0 for line in lines]

    # Trigramas: inferior = líneas 1-3, superior = líneas 4-6
    lower_trigram = "".join(str(b) for b in primary_bits[0:3])
    upper_trigram = "".join(str(b) for b in primary_bits[3:6])

    primary_number = _KING_WEN_TABLE.get((upper_trigram, lower_trigram))
    primary_info = get_hexagram_info(primary_number) if primary_number else None

    result = {
        "lines": lines,
        "primary": primary_number,
        "primary_name": primary_info["name"] if primary_info else "Desconocido",
        "primary_spanish": primary_info["spanish"] if primary_info else "",
        "primary_chinese": primary_info["chinese"] if primary_info else "",
        "derived": None,
        "derived_name": None,
        "derived_spanish": None,
        "derived_chinese": None,
        "mutable_lines": mutable_lines,
    }

    # Si hay líneas mutables, calcular hexagrama derivado
    if mutable_lines:
        # Mutar: yang viejo (9) → yin (0), yin viejo (6) → yang (1)
        derived_bits = []
        for line in lines:
            if line == 9:
                derived_bits.append(0)  # yang viejo muta a yin
            elif line == 6:
                derived_bits.append(1)  # yin viejo muta a yang
            else:
                derived_bits.append(1 if line == 7 else 0)

        d_lower = "".join(str(b) for b in derived_bits[0:3])
        d_upper = "".join(str(b) for b in derived_bits[3:6])

        derived_number = _KING_WEN_TABLE.get((d_upper, d_lower))
        derived_info = get_hexagram_info(derived_number) if derived_number else None

        result["derived"] = derived_number
        result["derived_name"] = derived_info["name"] if derived_info else "Desconocido"
        result["derived_spanish"] = derived_info["spanish"] if derived_info else ""
        result["derived_chinese"] = derived_info["chinese"] if derived_info else ""

    return result


def build_drawn_data(hexagram: dict) -> dict:
    """Construye drawn_data JSON para usage_log."""
    return {
        "hexagram": {
            "lines": hexagram["lines"],
            "primary": hexagram["primary"],
            "primary_name": hexagram["primary_name"],
            "derived": hexagram["derived"],
            "derived_name": hexagram["derived_name"],
            "mutable_lines": hexagram["mutable_lines"],
        }
    }
