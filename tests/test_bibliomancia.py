"""Tests de bibliomancia: carga datos, fragmentos, anti-repetición, split."""

import pytest

import bot.handlers.bibliomancia as biblio_mod
from bot.handlers.bibliomancia import (
    _get_random_fragment,
    _load_texts,
    _split_long_message,
)


@pytest.fixture(autouse=True)
def load_texts():
    """Cargar textos antes de cada test."""
    _load_texts()


def test_texts_loaded():
    """Los 4 textos se cargan correctamente."""
    _load_texts()
    assert biblio_mod._TEXTS is not None
    assert "biblia" in biblio_mod._TEXTS
    assert "coran" in biblio_mod._TEXTS
    assert "gita" in biblio_mod._TEXTS
    assert "evangelio" in biblio_mod._TEXTS


def test_texts_not_empty():
    """Cada texto tiene al menos una sección."""
    _load_texts()
    for key in ("biblia", "coran", "gita", "evangelio"):
        assert len(biblio_mod._TEXTS[key]) > 0, f"{key} está vacío"


def test_fragment_biblia():
    fragment = _get_random_fragment("biblia")
    assert fragment is not None
    assert "📖 Biblia" in fragment


def test_fragment_coran():
    fragment = _get_random_fragment("coran")
    assert fragment is not None
    assert "📖 Corán" in fragment


def test_fragment_gita():
    fragment = _get_random_fragment("gita")
    assert fragment is not None
    assert "📖 Bhagavad Gita" in fragment


def test_fragment_evangelio():
    fragment = _get_random_fragment("evangelio")
    assert fragment is not None
    assert "📖 Evangelio de Tomás" in fragment


def test_fragment_invalid_key():
    fragment = _get_random_fragment("inexistente")
    assert fragment is None


def test_anti_repetition():
    """No repite el mismo fragmento dos veces seguidas (excepto textos muy cortos)."""
    fragments = set()
    for _ in range(10):
        f = _get_random_fragment("biblia")
        if f:
            fragments.add(f)
    # Con muchas secciones, debería tener más de 1 fragmento distinto
    assert len(fragments) > 1


def test_split_short():
    chunks = _split_long_message("Hola mundo")
    assert len(chunks) == 1


def test_split_long():
    text = "A" * 5000
    chunks = _split_long_message(text, max_len=4096)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 4096


def test_split_preserves_content():
    text = "Línea 1\nLínea 2\nLínea 3"
    chunks = _split_long_message(text, max_len=20)
    joined = "\n".join(chunks)
    assert "Línea 1" in joined
    assert "Línea 3" in joined
