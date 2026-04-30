"""Calculadora de numerología pitagórica con normalización Unicode.

Método Decoz consistente en todos los cálculos basados en fecha:
reducir cada componente (día/mes/año) preservando maestros (11, 22, 33),
sumar los componentes reducidos y reducir el total preservando maestros.

- Camino de vida: día + mes + año de nacimiento.
- Año personal: día + mes de nacimiento + año actual.
- Mes personal: año personal + mes actual.
- Número de expresión: suma valores letras nombre completo.
- Número del alma: suma vocales nombre completo.
"""

import unicodedata
from datetime import datetime, timezone

from service.calculators.dates import parse_birth_date

# Tabla pitagórica: letra → número (1-9)
_PYTHAGOREAN_TABLE = {
    "a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8, "i": 9,
    "j": 1, "k": 2, "l": 3, "m": 4, "n": 5, "o": 6, "p": 7, "q": 8, "r": 9,
    "s": 1, "t": 2, "u": 3, "v": 4, "w": 5, "x": 6, "y": 7, "z": 8,
}

_VOWELS = set("aeiou")

# Números maestros que no se reducen
_MASTER_NUMBERS = {11, 22, 33}


def normalize_name(name: str) -> str:
    """Normaliza nombre para cálculo: ñ→n, á→a, quita no-letras.

    Pasos:
    1. NFD decompose: 'ñ' → 'n' + combining tilde, 'á' → 'a' + combining acute
    2. Quitar combining marks (categoría Mn)
    3. Lowercase
    4. Quedar solo con letras ASCII a-z
    """
    # NFD decompose
    decomposed = unicodedata.normalize("NFD", name)
    # Quitar combining marks
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    # Lowercase y solo letras
    return "".join(c.lower() for c in stripped if c.isalpha())


def _reduce_to_single(n: int) -> int:
    """Reduce un número a un solo dígito, respetando números maestros (11, 22, 33)."""
    while n > 9 and n not in _MASTER_NUMBERS:
        n = sum(int(d) for d in str(n))
    return n


def life_path(birth_date: str) -> int:
    """Camino de vida (Decoz): reducir día/mes/año por separado preservando
    maestros (11/22/33), sumar y reducir el total preservando maestros."""
    day, month, year = parse_birth_date(birth_date)
    total = (
        _reduce_to_single(day)
        + _reduce_to_single(month)
        + _reduce_to_single(year)
    )
    return _reduce_to_single(total)


def expression_number(full_name: str) -> int:
    """Número de expresión: suma de TODAS las letras del nombre completo."""
    normalized = normalize_name(full_name)
    total = sum(_PYTHAGOREAN_TABLE.get(c, 0) for c in normalized)
    return _reduce_to_single(total)


def soul_number(full_name: str) -> int:
    """Número del alma: suma de VOCALES del nombre completo."""
    normalized = normalize_name(full_name)
    total = sum(_PYTHAGOREAN_TABLE.get(c, 0) for c in normalized if c in _VOWELS)
    return _reduce_to_single(total)


def personality_number(full_name: str) -> int:
    """Número de personalidad: suma de CONSONANTES del nombre completo."""
    normalized = normalize_name(full_name)
    total = sum(_PYTHAGOREAN_TABLE.get(c, 0) for c in normalized if c not in _VOWELS)
    return _reduce_to_single(total)


def personal_year(birth_date: str, current_year: int | None = None) -> int:
    """Año personal (Decoz): día nacimiento + mes nacimiento + año actual,
    cada componente reducido preservando maestros antes de sumar."""
    if current_year is None:
        current_year = datetime.now(timezone.utc).year

    day, month, _ = parse_birth_date(birth_date)
    total = (
        _reduce_to_single(day)
        + _reduce_to_single(month)
        + _reduce_to_single(current_year)
    )
    return _reduce_to_single(total)


def personal_month(birth_date: str, current_year: int | None = None,
                   current_month: int | None = None) -> int:
    """Mes personal (Decoz): año personal + mes actual reducido, total
    reducido preservando maestros."""
    if current_year is None:
        current_year = datetime.now(timezone.utc).year
    if current_month is None:
        current_month = datetime.now(timezone.utc).month

    py = personal_year(birth_date, current_year)
    return _reduce_to_single(py + _reduce_to_single(current_month))


def full_report(birth_date: str, full_name: str | None = None,
                current_year: int | None = None,
                current_month: int | None = None) -> dict:
    """Informe numerológico completo."""
    report = {
        "life_path": life_path(birth_date),
        "personal_year": personal_year(birth_date, current_year),
        "personal_month": personal_month(birth_date, current_year, current_month),
    }

    if full_name:
        report["expression"] = expression_number(full_name)
        report["soul"] = soul_number(full_name)
        report["personality"] = personality_number(full_name)

    return report


def compatibility(birth_date_1: str, birth_date_2: str) -> dict:
    """Compatibilidad: solo caminos de vida."""
    lp1 = life_path(birth_date_1)
    lp2 = life_path(birth_date_2)
    return {
        "life_path_1": lp1,
        "life_path_2": lp2,
    }
