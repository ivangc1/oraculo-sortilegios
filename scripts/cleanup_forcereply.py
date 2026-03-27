#!/usr/bin/env python3
"""
Limpia ForceReply residuales buscando por texto exacto.
Usa concurrencia para escanear rápido.
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
from telegram.error import BadRequest, TimedOut, RetryAfter

# Subcadenas que identifican mensajes de ForceReply del bot
FORCEREPLY_MARKERS = [
    "Escribe tu pregunta para las cartas:",
    "Escribe tu pregunta para las runas:",
    "Escribe tu pregunta para el I Ching:",
    "Escribe tu pregunta para la geomancia:",
    "Escribe tu pregunta y yo decido qué tirada te conviene:",
    "Escribe tu pregunta:",
    "✍️ Escribe tu pregunta:",
    "¿Qué quieres saber?",
]

deleted_ids = []


def is_forcereply_text(text: str) -> bool:
    if not text:
        return False
    text = text.strip()
    return any(marker in text for marker in FORCEREPLY_MARKERS)


async def check_and_delete(bot: Bot, chat_id: int, admin_id: int, msg_id: int, sem: asyncio.Semaphore):
    async with sem:
        try:
            fwd = await bot.forward_message(
                chat_id=admin_id,
                from_chat_id=chat_id,
                message_id=msg_id,
            )
            text = fwd.text or ""

            # Borrar reenvío del DM siempre
            try:
                await bot.delete_message(chat_id=admin_id, message_id=fwd.message_id)
            except Exception:
                pass

            if is_forcereply_text(text):
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                deleted_ids.append(msg_id)
                print(f"  ✓ Borrado msg_id={msg_id} — \"{text.strip()[:60]}\"")

        except (BadRequest, TimedOut):
            pass
        except RetryAfter as e:
            print(f"  ⏳ Rate limit, esperando {e.retry_after}s...")
            await asyncio.sleep(e.retry_after)
        except Exception:
            pass


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
    print(f"Bot: @{me.username} (id={me.id})")
    print(f"Chat: {chat_id}\n")

    probe = await bot.send_message(chat_id=chat_id, text="🔧 Limpieza rápida...")
    latest_id = probe.message_id
    await bot.delete_message(chat_id=chat_id, message_id=latest_id)

    # Rango grande: 10000 IDs para cubrir varios días
    scan_range = 10000
    start_id = max(1, latest_id - scan_range)
    print(f"Escaneando {start_id} → {latest_id} ({scan_range} IDs)...")

    sem = asyncio.Semaphore(10)

    batch_size = 100
    for batch_start in range(start_id, latest_id, batch_size):
        batch_end = min(batch_start + batch_size, latest_id)
        tasks = [
            check_and_delete(bot, chat_id, admin_id, msg_id, sem)
            for msg_id in range(batch_start, batch_end)
        ]
        await asyncio.gather(*tasks)
        pct = int((batch_end - start_id) / scan_range * 100)
        print(f"  ... {pct}%")

    print(f"\n{'='*40}")
    print(f"ForceReply borrados: {len(deleted_ids)}")
    if deleted_ids:
        print(f"IDs: {deleted_ids}")
    await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
