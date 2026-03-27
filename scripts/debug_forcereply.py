#!/usr/bin/env python3
"""Diagnóstico: reenvía mensajes específicos y muestra el texto crudo."""

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
from telegram.error import BadRequest

TARGET_IDS = [914907, 915505]


async def main():
    token = os.environ.get("BOT_TOKEN")
    chat_id = int(os.environ.get("ALLOWED_CHAT_ID"))
    admin_id = int(os.environ.get("ADMIN_USER_ID"))
    bot = Bot(token=token)

    me = await bot.get_me()
    print(f"Bot id: {me.id}\n")

    for msg_id in TARGET_IDS:
        print(f"--- msg_id={msg_id} ---")
        try:
            fwd = await bot.forward_message(
                chat_id=admin_id,
                from_chat_id=chat_id,
                message_id=msg_id,
            )
            print(f"  from_user: {fwd.from_user}")
            print(f"  forward_origin: {fwd.forward_origin}")
            print(f"  text: {repr(fwd.text)}")
            print(f"  caption: {repr(fwd.caption)}")
            print(f"  photo: {bool(fwd.photo)}")
            print(f"  sticker: {bool(fwd.sticker)}")

            # Borrar reenvío
            await bot.delete_message(chat_id=admin_id, message_id=fwd.message_id)
        except BadRequest as e:
            print(f"  ERROR: {e}")
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
        print()

    await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
