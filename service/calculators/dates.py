"""Parsing común de fecha de nacimiento — `DD/MM/AAAA` o `AAAA-MM-DD`.

Centralizado aquí para que numerologia, timezone y natal compartan una
sola implementación. Si el formato cambia o se añade variante, un solo sitio
que tocar.
"""

from __future__ import annotations


def parse_birth_date(birth_date: str) -> tuple[int, int, int]:
    """Parsea una fecha de nacimiento a `(day, month, year)` enteros.

    Acepta ambos formatos canónicos del bot:
    - `DD/MM/AAAA` (formato del onboarding del usuario).
    - `AAAA-MM-DD` (ISO, usado en algunos paths internos).

    Lanza `ValueError` si no reconoce el separador.
    """
    if "/" in birth_date:
        parts = birth_date.split("/")
        day, month, year = parts[0], parts[1], parts[2]
    elif "-" in birth_date:
        parts = birth_date.split("-")
        year, month, day = parts[0], parts[1], parts[2]
    else:
        raise ValueError(f"Formato de fecha no reconocido: {birth_date}")
    return int(day), int(month), int(year)
