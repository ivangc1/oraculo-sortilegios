"""Dashboard admin: /stats, /version. Solo ADMIN_USER_ID.

No-admin → respuesta in-character (no silencio).
/stats limitado a top 5. Si >4096, split.
"""

import time

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import Settings
from bot.formatting import split_message
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from database import usage as db_usage
from database import feedback as db_feedback


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /stats — solo admin."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    if update.effective_user.id != settings.ADMIN_USER_ID:
        await update.message.reply_text(
            LIMIT_MESSAGES["admin_only"],
            reply_to_message_id=update.message.message_id,
        )
        return

    stats = await db_usage.get_stats_summary()
    fb_stats = await db_feedback.get_feedback_stats()
    daily_cost = await db_usage.get_daily_cost()
    monthly_cost = await db_usage.get_monthly_cost()

    # BOT_START_TIME
    from bot.main import BOT_START_TIME
    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    lines = [
        f"📊 Estadísticas del Oráculo",
        f"",
        f"Uptime: {uptime_str}",
        f"Total consultas: {stats['total_uses']}",
        f"Coste total: ${stats['total_cost']:.4f}",
        f"Coste hoy: ${daily_cost:.4f}",
        f"Coste mes: ${monthly_cost:.4f}",
        f"Límite mes: ${settings.MONTHLY_SPENDING_LIMIT:.2f}",
        f"Cache hit rate: {stats['cache_rate']:.1f}%",
        f"Truncadas: {stats['truncated_count']}",
        f"",
        f"Top 5 usuarios:",
    ]
    for u in stats["top_users"]:
        lines.append(f"  {u['alias']}: {u['uses']} usos (${u['cost']:.4f})")

    if not stats["top_users"]:
        lines.append("  (ningún uso registrado)")

    lines.append("")
    lines.append("Por modo:")
    for m in stats["by_mode"]:
        lines.append(f"  {m['mode']}: {m['uses']}")

    if not stats["by_mode"]:
        lines.append("  (ningún uso registrado)")

    lines.append("")
    lines.append(f"Feedback: 👍 {fb_stats['positive']} / 👎 {fb_stats['negative']} (total: {fb_stats['total']})")
    lines.append(f"Tokens input: {stats['total_input_tokens']:,}")
    lines.append(f"Tokens output: {stats['total_output_tokens']:,}")

    text = "\n".join(lines)
    chunks = split_message(text)
    for chunk in chunks:
        await update.message.reply_text(
            chunk, reply_to_message_id=update.message.message_id,
        )


async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /version — solo admin."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    if update.effective_user.id != settings.ADMIN_USER_ID:
        await update.message.reply_text(
            LIMIT_MESSAGES["admin_only"],
            reply_to_message_id=update.message.message_id,
        )
        return

    await update.message.reply_text(
        f"🔮 El Oráculo de los Sortilegios v{settings.BOT_VERSION}\n"
        f"Env: {settings.ENV}",
        reply_to_message_id=update.message.message_id,
    )
