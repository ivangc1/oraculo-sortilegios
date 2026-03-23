"""Calculadora de numerología pitagórica con normalización Unicode.

Camino de vida: suma dígitos fecha nacimiento, reducir a 1 dígito (excepto 11, 22, 33).
Número de expresión: suma valores letras nombre completo.
Número del alma: suma vocales nombre completo.
Año personal: suma día + mes nacimiento + año actual.
Mes personal: año personal + mes actual.
"""

import unicodedata
from datetime import datetime, timezone

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


def _sum_digits(number_str: str) -> int:
    """Suma dígitos de una cadena numérica."""
    return sum(int(d) for d in number_str if d.isdigit())


def life_path(birth_date: str) -> int:
    """Calcula camino de vida desde fecha DD/MM/AAAA o AAAA-MM-DD.

    Método: reducir día, mes, año por separado, luego sumar y reducir.
    """
    # Parsear fecha
    if "/" in birth_date:
        parts = birth_date.split("/")
        day, month, year = parts[0], parts[1], parts[2]
    elif "-" in birth_date:
        parts = birth_date.split("-")
        year, month, day = parts[0], parts[1], parts[2]
    else:
        raise ValueError(f"Formato de fecha no reconocido: {birth_date}")

    day_reduced = _reduce_to_single(_sum_digits(day))
    month_reduced = _reduce_to_single(_sum_digits(month))
    year_reduced = _reduce_to_single(_sum_digits(year))

    total = day_reduced + month_reduced + year_reduced
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
    """Año personal: día nacimiento + mes nacimiento + año actual."""
    if current_year is None:
        current_year = datetime.now(timezone.utc).year

    if "/" in birth_date:
        parts = birth_date.split("/")
        day, month = parts[0], parts[1]
    elif "-" in birth_date:
        parts = birth_date.split("-")
        day, month = parts[2], parts[1]
    else:
        raise ValueError(f"Formato de fecha no reconocido: {birth_date}")

    day_val = _sum_digits(day)
    month_val = _sum_digits(month)
    year_val = _sum_digits(str(current_year))

    return _reduce_to_single(day_val + month_val + year_val)


def personal_month(birth_date: str, current_year: int | None = None,
                   current_month: int | None = None) -> int:
    """Mes personal: año personal + mes actual."""
    if current_year is None:
        current_year = datetime.now(timezone.utc).year
    if current_month is None:
        current_month = datetime.now(timezone.utc).month

    py = personal_year(birth_date, current_year)
    return _reduce_to_single(py + current_month)


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
