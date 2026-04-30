"""Tests de simetría entre los 72 demonios Goetia y los 72 ángeles Shem.

Convención canónica (Mathers, Crowley, tradición de la Cábala): el ángel N
del Shem HaMephorash contrarresta al demonio N del Ars Goetia. Vehuiah ↔ Bael
(ambos #1), y así con los 72.

Si esto se rompe (por reordenación accidental de los datos o por edición
manual), la simetría se cruza y el bot mezcla correspondencias en /demonio
y /angel.
"""

from bot.handlers.angel import _load_data as _load_angel_data
from bot.handlers.demonio import _load_data as _load_demon_data


def test_shem_corresponding_demon_simetrico():
    """SHEM[i].corresponding_demon == i+1 para los 72 ángeles."""
    _load_angel_data()
    from bot.handlers.angel import _SHEM
    assert len(_SHEM) == 72
    for i, angel in enumerate(_SHEM):
        expected = i + 1
        assert angel["number"] == expected, f"SHEM[{i}].number={angel['number']}, esperaba {expected}"
        cd = angel.get("corresponding_demon")
        assert cd == expected, (
            f"SHEM[{i}] ({angel['name']}) corresponding_demon={cd}, esperaba {expected}"
        )


def test_goetia_corresponding_angel_simetrico():
    """GOETIA[i].corresponding_angel == i+1 para los 72 demonios."""
    _load_demon_data()
    from bot.handlers.demonio import _GOETIA
    assert len(_GOETIA) == 72
    for i, demon in enumerate(_GOETIA):
        expected = i + 1
        assert demon["number"] == expected, f"GOETIA[{i}].number={demon['number']}, esperaba {expected}"
        ca = demon.get("corresponding_angel")
        assert ca == expected, (
            f"GOETIA[{i}] ({demon['name']}) corresponding_angel={ca}, esperaba {expected}"
        )


def test_shem_y_goetia_misma_longitud():
    """Ambos sets tienen exactamente 72 entradas (canon)."""
    _load_angel_data()
    _load_demon_data()
    from bot.handlers.angel import _SHEM
    from bot.handlers.demonio import _GOETIA
    assert len(_SHEM) == len(_GOETIA) == 72
