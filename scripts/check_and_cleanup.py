#!/usr/bin/env python3
"""
Borra TODOS los mensajes del bot en el grupo (rango amplio).
Sin can_delete_messages, solo podrá borrar sus propios mensajes.
Primero muestra permisos, luego barre por fuerza bruta.
"""

import asyncio
import os
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from telegram import Bot
from telegram.error import BadRequest, Forbidden, RetryAfter

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["ALLOWED_CHAT_ID"])

LAST_KNOWN = 915505
RANGE_SIZE = 20000
BATCH = 30


async def main():
    bot = Bot(token=TOKEN)
    me = await bot.get_me()
    print(f"Bot: @{me.username} (id={me.id})")
    print(f"Chat: {CHAT_ID}\n")

    # Verificar permisos
    print("=" * 40)
    print("PERMISOS DEL BOT:")
    print("=" * 40)
    member = await bot.get_chat_member(chat_id=CHAT_ID, user_id=me.id)
    print(f"  status: {member.status}")
    can_del = getattr(member, "can_delete_messages", None)
    print(f"  can_delete_messages: {can_del}")
    print()

    if can_del:
        print("⚠️  ATENCION: el bot PUEDE borrar mensajes ajenos.")
        print("   Quítale ese permiso primero para no borrar mensajes de usuarios.")
        print("   Abortando.")
        await bot.shutdown()
        return

    # Barrido: intentar delete en todo el rango
    start_id = LAST_KNOWN - RANGE_SIZE
    end_id = LAST_KNOWN + 1000
    total = end_id - start_id
    print(f"Barriendo {start_id} → {end_id} ({total} IDs)...")
    print("(Solo borrará mensajes del propio bot)\n")

    deleted = 0
    errors = 0
    count = 0

    for msg_id in range(start_id, end_id + 1):
        count += 1
        if count % 1000 == 0:
            pct = int(count / total * 100)
            print(f"  ... {pct}% (borrados: {deleted})")

        try:
            await bot.delete_message(chat_id=CHAT_ID, message_id=msg_id)
            deleted += 1
            print(f"  ✓ Borrado msg_id={msg_id}")
        except BadRequest:
            pass  # no existe o no es del bot
        except Forbidden:
            pass  # no tiene permiso (mensaje ajeno)
        except RetryAfter as e:
            print(f"  ⏳ Rate limit, esperando {e.retry_after}s...")
            await asyncio.sleep(e.retry_after + 1)
            continue
        except Exception:
            errors += 1

        if count % BATCH == 0:
            await asyncio.sleep(0.3)

    print(f"\n{'=' * 40}")
    print(f"Mensajes del bot borrados: {deleted}")
    print(f"Errores: {errors}")

    await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
