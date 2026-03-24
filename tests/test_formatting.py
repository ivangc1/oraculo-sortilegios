"""Tests de formateo: marcadores custom + html.escape + split + blockquote."""

from bot.formatting import (
    format_response, split_message,
    wrap_blockquote, format_and_split,
    _close_open_tags, _reopen_tags_from_previous,
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
    assert "<b>" in result


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


# === Tag balancing ===

def test_close_open_tags_bold():
    """Cierra <b> abierto."""
    result = _close_open_tags("Texto <b>abierto")
    assert result == "Texto <b>abierto</b>"


def test_close_open_tags_italic():
    """Cierra <i> abierto."""
    result = _close_open_tags("La carta <i>El Loco")
    assert result == "La carta <i>El Loco</i>"


def test_close_open_tags_both():
    """Cierra ambos tags abiertos."""
    result = _close_open_tags("<b>Titulo <i>carta")
    assert result.endswith("</i></b>")


def test_close_open_tags_balanced():
    """No modifica texto con tags balanceados."""
    text = "<b>ok</b> y <i>bien</i>"
    assert _close_open_tags(text) == text


def test_reopen_tags_from_previous():
    """Detecta tags abiertos en chunk previo."""
    prev = "<b>Titulo <i>carta"
    reopen = _reopen_tags_from_previous(prev)
    assert "<b>" in reopen
    assert "<i>" in reopen


def test_reopen_tags_none_needed():
    """Sin tags abiertos no genera nada."""
    prev = "<b>ok</b>"
    assert _reopen_tags_from_previous(prev) == ""


# === Blockquote ===

def test_wrap_blockquote():
    """Blockquote expandible."""
    result = wrap_blockquote("Texto largo")
    assert "<blockquote expandable>" in result
    assert "</blockquote>" in result


def test_wrap_blockquote_closes_tags():
    """Blockquote cierra tags abiertos dentro."""
    result = wrap_blockquote("La carta <i>El Loco")
    assert "</i>" in result
    assert result.index("</i>") < result.index("</blockquote>")


def test_format_and_split_blockquote_true():
    """use_blockquote=True envuelve todos los chunks."""
    raw = "[[T]]Titulo[[/T]]\nTexto"
    chunks = format_and_split(raw, use_blockquote=True)
    assert len(chunks) == 1
    assert "<blockquote expandable>" in chunks[0]
    assert "<b>Titulo</b>" in chunks[0]


def test_format_and_split_blockquote_false():
    """use_blockquote=False devuelve HTML limpio sin blockquote."""
    raw = "[[T]]Titulo[[/T]]\nTexto"
    chunks = format_and_split(raw, use_blockquote=False)
    assert len(chunks) == 1
    assert "<blockquote" not in chunks[0]
    assert "<b>Titulo</b>" in chunks[0]


def test_format_and_split_long_with_blockquote():
    """Texto largo con blockquote: cada chunk envuelto y tags balanceados."""
    para = "A" * 2000
    raw = f"[[T]]{para}[[/T]]\n\n{para}\n\n{para}"
    chunks = format_and_split(raw, use_blockquote=True)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert "<blockquote expandable>" in chunk
        assert "</blockquote>" in chunk


def test_format_and_split_default_no_blockquote():
    """Por defecto (sin argumento) no aplica blockquote."""
    raw = "Texto normal"
    chunks = format_and_split(raw)
    assert "<blockquote" not in chunks[0]


def test_format_and_split_unclosed_italic_in_split():
    """Si split corta en medio de un <i>, los chunks quedan balanceados."""
    raw = "[[C]]" + "X" * 3000 + "[[/C]]\n\n" + "Segundo parrafo"
    chunks = format_and_split(raw, use_blockquote=True)
    for chunk in chunks:
        # Cada chunk debe tener tags balanceados dentro del blockquote
        inner = chunk.replace("<blockquote expandable>", "").replace("</blockquote>", "")
        assert inner.count("<i>") == inner.count("</i>"), f"Unbalanced <i> in: {chunk[:100]}"
        assert inner.count("<b>") == inner.count("</b>"), f"Unbalanced <b> in: {chunk[:100]}"
