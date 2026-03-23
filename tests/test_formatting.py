"""Tests de formateo: marcadores custom + html.escape + split."""

from bot.formatting import format_response, split_message


def test_format_markers():
    """[[T]] y [[C]] se convierten a HTML bold/italic."""
    raw = "[[T]]El Pasado[[/T]]\nLa carta [[C]]El Loco[[/C]] invertida."
    result = format_response(raw)
    assert "<b>El Pasado</b>" in result
    assert "<i>El Loco</i>" in result


def test_format_html_escape():
    """& < > se escapan antes de aplicar marcadores."""
    raw = "[[T]]Sección & <título>[[/T]]"
    result = format_response(raw)
    assert "&amp;" in result
    assert "&lt;" in result
    assert "&gt;" in result
    assert "<b>" in result  # Nuestros marcadores sí se aplican


def test_format_no_markers():
    """Texto sin marcadores se devuelve escapado sin cambios."""
    raw = "Texto simple sin marcadores"
    result = format_response(raw)
    assert result == "Texto simple sin marcadores"


def test_split_short_message():
    """Mensaje corto no se divide."""
    text = "Hola mundo"
    chunks = split_message(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_long_message():
    """Mensaje largo se divide por párrafos."""
    para = "A" * 2000
    text = f"{para}\n\n{para}\n\n{para}"
    chunks = split_message(text, max_length=4096)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 4096


def test_split_preserves_content():
    """Split no pierde contenido."""
    text = "Párrafo 1\n\nPárrafo 2\n\nPárrafo 3"
    chunks = split_message(text, max_length=25)
    joined = "\n\n".join(chunks)
    assert "Párrafo 1" in joined
    assert "Párrafo 2" in joined
    assert "Párrafo 3" in joined
