"""Formateo: html.escape + marcadores custom [[T]][[C]] → HTML."""

import html
import textwrap


def format_response(raw_text: str) -> str:
    """Convierte texto plano con marcadores custom a HTML seguro para Telegram."""
    safe = html.escape(raw_text)
    safe = safe.replace("[[T]]", "<b>").replace("[[/T]]", "</b>")
    safe = safe.replace("[[C]]", "<i>").replace("[[/C]]", "</i>")
    return safe


def split_message(text: str, max_length: int = 4096) -> list[str]:
    """Divide mensaje largo en fragmentos ≤ max_length respetando párrafos."""
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
            # Si un párrafo solo excede max_length, cortar con textwrap
            if len(para) > max_length:
                wrapped = textwrap.wrap(para, width=max_length, break_long_words=True, break_on_hyphens=False)
                chunks.extend(wrapped)
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks
