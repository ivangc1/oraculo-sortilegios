"""Tests de formateo: marcadores custom + html.escape + split + spoiler."""

from bot.formatting import (
    format_response, split_message, wrap_spoiler,
    wrap_blockquote, format_and_split,
)


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


# === Spoiler + Blockquote ===

def test_wrap_spoiler():
    """Spoiler envuelve en tg-spoiler."""
    result = wrap_spoiler("Texto secreto")
    assert result == "<tg-spoiler>Texto secreto</tg-spoiler>"


def test_wrap_blockquote():
    """Blockquote expandible."""
    result = wrap_blockquote("Texto largo")
    assert result == "<blockquote expandable>Texto largo</blockquote>"


def test_format_and_split_with_spoiler():
    """format_and_split aplica spoiler con intro."""
    raw = "[[T]]Titulo[[/T]]\nTexto de prueba"
    chunks = format_and_split(raw, spoiler=True)
    assert len(chunks) == 1
    assert "<tg-spoiler>" in chunks[0]
    assert "<b>Titulo</b>" in chunks[0]
    assert "Pulsa" in chunks[0]  # Intro visible antes del spoiler


def test_format_and_split_without_spoiler():
    """format_and_split sin spoiler devuelve HTML limpio."""
    raw = "[[T]]Titulo[[/T]]\nTexto"
    chunks = format_and_split(raw, spoiler=False)
    assert len(chunks) == 1
    assert "<tg-spoiler>" not in chunks[0]
    assert "<b>Titulo</b>" in chunks[0]


def test_format_and_split_long_text_spoiler():
    """Texto largo con spoiler: cada chunk tiene spoiler, intro solo en el primero."""
    para = "A" * 2000
    raw = f"{para}\n\n{para}\n\n{para}"
    chunks = format_and_split(raw, spoiler=True)
    assert len(chunks) >= 2
    # Primer chunk tiene intro + spoiler
    assert "Pulsa" in chunks[0]
    assert "<tg-spoiler>" in chunks[0]
    # Resto solo spoiler
    for chunk in chunks[1:]:
        assert "<tg-spoiler>" in chunk
        assert "Pulsa" not in chunk
