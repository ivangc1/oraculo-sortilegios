"""Formateo: html.escape + marcadores custom [[T]][[C]] -> HTML.

Soporte para expandable blockquote de Telegram Bot API 7.0+.
Cierra tags abiertos antes de wrapping para evitar HTML malformado.
"""

import html
import re
import textwrap


def format_response(raw_text: str) -> str:
    """Convierte texto plano con marcadores custom a HTML seguro para Telegram."""
    safe = html.escape(raw_text)
    safe = safe.replace("[[T]]", "<b>").replace("[[/T]]", "</b>")
    safe = safe.replace("[[C]]", "<i>").replace("[[/C]]", "</i>")
    return safe


def _close_open_tags(text: str) -> str:
    """Cierra tags HTML abiertos al final del texto y reabre al inicio si es necesario.

    Solo maneja <b>, <i>, <tg-spoiler> — los unicos que usamos.
    Devuelve el texto con tags balanceados.
    """
    tags = ["b", "i"]
    open_tags = []
    for tag in tags:
        open_count = len(re.findall(f"<{tag}>", text))
        close_count = len(re.findall(f"</{tag}>", text))
        if open_count > close_count:
            open_tags.append(tag)
    # Cerrar en orden inverso (LIFO)
    for tag in reversed(open_tags):
        text += f"</{tag}>"
    return text


def _reopen_tags_from_previous(prev_chunk: str) -> str:
    """Detecta tags que quedaron abiertos al final del chunk anterior
    y devuelve los tags de apertura para prepend al siguiente chunk."""
    tags = ["b", "i"]
    reopen = []
    for tag in tags:
        open_count = len(re.findall(f"<{tag}>", prev_chunk))
        close_count = len(re.findall(f"</{tag}>", prev_chunk))
        if open_count > close_count:
            reopen.append(tag)
    return "".join(f"<{tag}>" for tag in reopen)


def wrap_blockquote(text: str) -> str:
    """Envuelve texto en blockquote expandible. Cierra tags abiertos primero."""
    text = _close_open_tags(text)
    return f"<blockquote expandable>{text}</blockquote>"


def format_and_split(raw_text: str, use_blockquote: bool = False) -> list[str]:
    """Pipeline completo: format -> split -> balance tags -> blockquote opcional.

    Args:
        raw_text: texto crudo del LLM con marcadores [[T]] [[C]]
        use_blockquote: si True, TODOS los chunks se envuelven en
            blockquote expandible (colapsado en el chat).

    Returns:
        Lista de chunks HTML listos para enviar con parse_mode="HTML"
    """
    formatted = format_response(raw_text)
    # Reservar espacio para overhead de tags de balanceo y blockquote.
    # Blockquote: <blockquote expandable>...</blockquote> = 42 chars
    # Tags balanceo: peor caso </i></b> + <b><i> = ~14 chars
    # Margen de seguridad: 60 chars
    overhead = 60 if use_blockquote else 16
    chunks = split_message(formatted, max_length=4096 - overhead)

    # Balancear tags entre chunks
    balanced = []
    for i, chunk in enumerate(chunks):
        if i > 0:
            reopen = _reopen_tags_from_previous(chunks[i - 1])
            chunk = reopen + chunk
        chunk = _close_open_tags(chunk)
        balanced.append(chunk)

    if use_blockquote:
        balanced = [wrap_blockquote(c) for c in balanced]
    return balanced


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
