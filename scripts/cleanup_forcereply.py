#!/usr/bin/env python3
"""
Limpia mensajes del bot con ForceReply residual buscando por texto exacto.
Solo borra mensajes que contengan los textos que acompañaban al ForceReply.

Uso (en el servidor):
  cd /opt/oraculo-sortilegios
  sudo systemctl stop oraculo
  python3 scripts/cleanup_forcereply.py
  sudo systemctl start oraculo
"""

import asyncio
import os
import sys
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from telegram import Bot
from telegram.error import BadRequest, TimedOut

# Textos exactos que el bot enviaba con ForceReply
FORCEREPLY_TEXTS = {
    "✍️ Escribe tu pregunta:",
    "¿Qué quieres saber?",
}


async def main():
    token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("ALLOWED_CHAT_ID")
    admin_id = os.environ.get("ADMIN_USER_ID")
    if not token or not chat_id or not admin_id:
        print("ERROR: BOT_TOKEN, ALLOWED_CHAT_ID y ADMIN_USER_ID deben estar en .env")
        sys.exit(1)

    chat_id = int(chat_id)
    admin_id = int(admin_id)
    bot = Bot(token=token)

    me = await bot.get_me()
    bot_id = me.id
    print(f"Bot: @{me.username} (id={bot_id})")
    print(f"Chat: {chat_id}")
    print(f"Buscando textos: {FORCEREPLY_TEXTS}\n")

    # Mensaje sonda para obtener el message_id más reciente
    probe = await bot.send_message(chat_id=chat_id, text="🔧 Buscando ForceReply residuales...")
    latest_id = probe.message_id
    await bot.delete_message(chat_id=chat_id, message_id=latest_id)

    scan_range = 2000
    start_id = max(1, latest_id - scan_range)
    deleted = 0
    checked = 0

    print(f"Escaneando message_ids {start_id} → {latest_id}...")

    for msg_id in range(start_id, latest_id):
        try:
            # Reenviar al DM del admin para leer el contenido
            fwd = await bot.forward_message(
                chat_id=admin_id,
                from_chat_id=chat_id,
                message_id=msg_id,
            )
            checked += 1

            # Comprobar si el texto coincide con un ForceReply
            text = (fwd.text or "").strip()
            is_forcereply = text in FORCEREPLY_TEXTS

            # Borrar el reenvío del DM siempre
            try:
                await bot.delete_message(chat_id=admin_id, message_id=fwd.message_id)
            except Exception:
                pass

            if is_forcereply:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                deleted += 1
                print(f"  ✓ Borrado msg_id={msg_id} — \"{text}\"")

        except BadRequest:
            pass  # No existe
        except TimedOut:
            await asyncio.sleep(3)
        except Exception:
            pass

        # Rate limit
        if checked % 20 == 0:
            await asyncio.sleep(1)

    print(f"\n{'='*40}")
    print(f"Escaneados: {checked} | ForceReply borrados: {deleted}")
    await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
