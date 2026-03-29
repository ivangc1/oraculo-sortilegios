"""Handler de bibliomancia: fragmentos de textos sagrados (€0 API).

Dos vías de acceso:
- /bibliomancia → Grid de 4 botones inline
- /bibliomancia biblia → Fragmento aleatorio directo

Anti-repetición: no repite último fragmento por texto.
Mensajes >4096: split con párrafos.
"""

import random
import textwrap

from loguru import logger
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.config import Settings
from bot.formatting import wrap_blockquote
from bot.keyboards import bibliomancia_keyboard
from bot.middleware import middleware_check
from bot.typing import get_thread_id

_rng = random.SystemRandom()

# Datos cargados en memoria al primer uso
_TEXTS: dict[str, dict] | None = None
_LAST_FRAGMENT: dict[str, str] = {}  # {texto_key: último fragmento enviado}

# Encoding del archivo de datos
_DATA_ENCODING = "utf-8"


def _load_texts() -> None:
    """Carga los 4 textos sagrados desde bibliomancia_datos.py."""
    global _TEXTS
    if _TEXTS is not None:
        return

    import importlib.util
    from pathlib import Path

    data_path = Path(__file__).parent.parent.parent / "data" / "bibliomancia_datos.py"

    # Leer con encoding correcto y compilar
    with open(data_path, encoding=_DATA_ENCODING) as f:
        source = f.read()

    namespace = {}
    exec(compile(source, str(data_path), "exec"), namespace)

    _TEXTS = {
        "biblia": namespace.get("BIBLIA", {}),
        "coran": namespace.get("CORAN", {}),
        "gita": namespace.get("GITA", {}),
        "evangelio": namespace.get("EVANGELIO", {}),
    }

    logger.info(
        f"Bibliomancia cargada: "
        f"Biblia={len(_TEXTS['biblia'])} secciones, "
        f"Corán={len(_TEXTS['coran'])} suras, "
        f"Gita={len(_TEXTS['gita'])} capítulos, "
        f"Evangelio={len(_TEXTS['evangelio'])} secciones"
    )


def _get_random_fragment(text_key: str) -> str | None:
    """Selecciona fragmento aleatorio sin repetir el último.

    Maneja 3 formatos de datos:
    - dict (CORAN): {sección: [[num, texto], ...]}
    - list of str (BIBLIA, EVANGELIO): ["verso1", "verso2", ...]
    - list of dict (GITA): [{"id": 1, "verso": 1, "texto": "..."}, ...]
    """
    _load_texts()
    text_data = _TEXTS.get(text_key)
    if not text_data:
        return None

    n_block = _rng.randint(3, 7)

    if isinstance(text_data, dict):
        # CORAN: dict de secciones
        sections = list(text_data.keys())
        section = _rng.choice(sections)
        verses = text_data[section]
        n_block = min(len(verses), n_block)
        start = _rng.randint(0, max(0, len(verses) - n_block))
        selected = verses[start:start + n_block]
        lines = []
        for v in selected:
            if isinstance(v, list) and len(v) >= 2:
                lines.append(str(v[1]))
            else:
                lines.append(str(v))
        fragment_text = "\n".join(lines)
        ref = section

    elif isinstance(text_data, list):
        total = len(text_data)
        n_block = min(total, n_block)
        start = _rng.randint(0, max(0, total - n_block))
        selected = text_data[start:start + n_block]
        lines = []
        for v in selected:
            if isinstance(v, dict):
                # GITA: {"id": N, "verso": N, "texto": "..."}
                lines.append(str(v.get("texto", v)))
            else:
                lines.append(str(v))
        fragment_text = "\n".join(lines)
        ref = f"fragmento {start + 1}-{start + n_block}"
    else:
        return None

    # Anti-repetición
    last = _LAST_FRAGMENT.get(text_key)
    if fragment_text == last:
        # Otro intento con posición diferente
        if isinstance(text_data, dict):
            sections = list(text_data.keys())
            if len(sections) > 1:
                other = [s for s in sections if s != section]
                section = _rng.choice(other)
                verses = text_data[section]
                n_block = min(len(verses), _rng.randint(3, 7))
                start = _rng.randint(0, max(0, len(verses) - n_block))
                selected = verses[start:start + n_block]
                lines = [str(v[1]) if isinstance(v, list) and len(v) >= 2 else str(v) for v in selected]
                fragment_text = "\n".join(lines)
                ref = section
        elif isinstance(text_data, list) and len(text_data) > n_block:
            start = _rng.randint(0, max(0, len(text_data) - n_block))
            selected = text_data[start:start + n_block]
            lines = [str(v.get("texto", v)) if isinstance(v, dict) else str(v) for v in selected]
            fragment_text = "\n".join(lines)
            ref = f"fragmento {start + 1}-{start + n_block}"

    _LAST_FRAGMENT[text_key] = fragment_text

    labels = {
        "biblia": f"📖 Biblia — {ref}",
        "coran": f"📖 Corán — {ref}",
        "gita": f"📖 Bhagavad Gita — {ref}",
        "evangelio": f"📖 Evangelio de Tomás — {ref}",
    }
    header = labels.get(text_key, f"📖 {ref}")

    return f"{header}\n\n{fragment_text}"


def _split_long_message(text: str, max_len: int = 4096) -> list[str]:
    """Divide texto largo respetando líneas."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    lines = text.split("\n")
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 <= max_len:
            current = f"{current}\n{line}" if current else line
        else:
            if current:
                chunks.append(current)
            if len(line) > max_len:
                wrapped = textwrap.wrap(line, width=max_len)
                chunks.extend(wrapped)
                current = ""
            else:
                current = line
    if current:
        chunks.append(current)
    return chunks


async def bibliomancia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /bibliomancia — grid o directo."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    # Comprobar argumento directo: /bibliomancia biblia
    text = (update.message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        arg = parts[1].lower().strip()
        key_map = {
            "biblia": "biblia", "coran": "coran", "corán": "coran",
            "gita": "gita", "evangelio": "evangelio",
        }
        text_key = key_map.get(arg)
        if text_key:
            await _send_fragment(update, context, text_key)
            return

    # Sin argumento → grid de botones
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="¿De qué texto sagrado quieres un fragmento?",
        reply_markup=bibliomancia_keyboard(),
        message_thread_id=get_thread_id(update),
        reply_to_message_id=update.message.message_id,
    )


async def bibliomancia_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text_key: str,
) -> None:
    """Callback desde grid de botones."""
    settings: Settings = context.bot_data["settings"]
    query = update.callback_query
    await query.answer()
    await _send_fragment_from_callback(update, query, context, settings, text_key)


async def _send_fragment(update: Update, context, text_key: str) -> None:
    """Envía fragmento como mensaje nuevo."""
    settings: Settings = context.bot_data["settings"]
    fragment = _get_random_fragment(text_key)
    thread_id = get_thread_id(update)
    if not fragment:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No he encontrado textos de ese libro.",
            message_thread_id=thread_id,
            reply_to_message_id=update.message.message_id,
        )
        return

    use_bq = settings.use_blockquote_for("bibliomancia", text_key)
    chunks = _split_long_message(fragment)
    for chunk in chunks:
        text = wrap_blockquote(chunk) if use_bq else chunk
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode="HTML" if use_bq else None,
            message_thread_id=thread_id,
            reply_to_message_id=update.message.message_id,
        )


async def _send_fragment_from_callback(update, query, context, settings: Settings, text_key: str) -> None:
    """Envía fragmento editando el mensaje del callback."""
    fragment = _get_random_fragment(text_key)
    if not fragment:
        try:
            await query.edit_message_text("No he encontrado textos de ese libro.")
        except BadRequest:
            pass
        return

    use_bq = settings.use_blockquote_for("bibliomancia", text_key)
    chunks = _split_long_message(fragment)
    first = wrap_blockquote(chunks[0]) if use_bq else chunks[0]
    try:
        await query.edit_message_text(first, parse_mode="HTML" if use_bq else None)
    except BadRequest:
        pass

    # Mensajes adicionales si excede 4096
    if len(chunks) > 1:
        chat_id = query.message.chat_id
        thread_id = get_thread_id(update)
        for chunk in chunks[1:]:
            text = wrap_blockquote(chunk) if use_bq else chunk
            await context.bot.send_message(
                chat_id, text=text,
                parse_mode="HTML" if use_bq else None,
                message_thread_id=thread_id,
            )
