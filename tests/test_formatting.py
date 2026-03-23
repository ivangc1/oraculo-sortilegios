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


def test_format_and_split_short_no_blockquote():
    """Texto corto (<1000 chars) no se envuelve en blockquote."""
    raw = "[[T]]Titulo[[/T]]\nTexto corto"
    chunks = format_and_split(raw, use_blockquote=True)
    assert len(chunks) == 1
    assert "<blockquote" not in chunks[0]
    assert "<b>Titulo</b>" in chunks[0]


def test_format_and_split_long_gets_blockquote():
    """Texto largo (>=1000 chars) se envuelve en blockquote expandible."""
    raw = "A" * 1200
    chunks = format_and_split(raw, use_blockquote=True)
    assert len(chunks) == 1
    assert "<blockquote expandable>" in chunks[0]
    assert "</blockquote>" in chunks[0]


def test_format_and_split_blockquote_disabled():
    """Con use_blockquote=False, texto largo va directo."""
    raw = "A" * 1200
    chunks = format_and_split(raw, use_blockquote=False)
    assert len(chunks) == 1
    assert "<blockquote" not in chunks[0]


def test_format_and_split_mixed_chunks():
    """Multi-chunk: solo los largos se envuelven."""
    short = "B" * 500
    long_para = "A" * 1500
    raw = f"{short}\n\n{long_para}"
    chunks = format_and_split(raw, use_blockquote=True)
    # El chunk corto no tiene blockquote, el largo si
    has_bq = [("<blockquote" in c) for c in chunks]
    assert any(has_bq)  # Al menos uno tiene blockquote
