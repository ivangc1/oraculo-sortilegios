"""Formateo: html.escape + marcadores custom [[T]][[C]] -> HTML.

Soporte para spoiler y expandable blockquote de Telegram Bot API 7.0+.
"""

import html
import textwrap

# Lecturas largas (>= este umbral de chars) usan expandable blockquote
_BLOCKQUOTE_THRESHOLD = 1500


def format_response(raw_text: str) -> str:
    """Convierte texto plano con marcadores custom a HTML seguro para Telegram."""
    safe = html.escape(raw_text)
    safe = safe.replace("[[T]]", "<b>").replace("[[/T]]", "</b>")
    safe = safe.replace("[[C]]", "<i>").replace("[[/C]]", "</i>")
    return safe


def wrap_spoiler(text: str) -> str:
    """Envuelve texto en spoiler de Telegram. El usuario pulsa para revelar."""
    return f"<tg-spoiler>{text}</tg-spoiler>"


def wrap_blockquote(text: str) -> str:
    """Envuelve texto en blockquote expandible. Se muestra colapsado."""
    return f"<blockquote expandable>{text}</blockquote>"


# Lecturas >= este umbral usan blockquote expandible
_BLOCKQUOTE_THRESHOLD = 1000


def format_and_split(raw_text: str, use_blockquote: bool = True) -> list[str]:
    """Pipeline completo: format -> split -> blockquote si largo.

    Args:
        raw_text: texto crudo del LLM con marcadores [[T]] [[C]]
        use_blockquote: si True, chunks largos (>=1000 chars) se envuelven
            en blockquote expandible (colapsado en el chat)

    Returns:
        Lista de chunks HTML listos para enviar con parse_mode="HTML"
    """
    formatted = format_response(raw_text)
    chunks = split_message(formatted)
    if use_blockquote:
        chunks = [
            wrap_blockquote(c) if len(c) >= _BLOCKQUOTE_THRESHOLD else c
            for c in chunks
        ]
    return chunks


def split_message(text: str, max_length: int = 4096) -> list[str]:
    """Divide mensaje largo en fragmentos <= max_length respetando parrafos."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_length:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # Si un parrafo solo excede max_length, cortar con textwrap
            if len(para) > max_length:
                wrapped = textwrap.wrap(para, width=max_length, break_long_words=True, break_on_hyphens=False)
                chunks.extend(wrapped)
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks
