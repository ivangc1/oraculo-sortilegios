"""Tareas programadas (JobQueue): limpieza caché membresía, resumen semanal."""

from loguru import logger
from telegram.ext import ContextTypes

from bot.middleware import cleanup_membership_cache
from database import usage as db_usage
from database import feedback as db_feedback


async def cleanup_membership_cache_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Limpia caché de membresía cada hora."""
    cleaned = cleanup_membership_cache()
    if cleaned > 0:
        logger.debug(f"Membership cache: {cleaned} entradas limpiadas")


async def send_weekly_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía resumen semanal al admin (domingos 9:00)."""
    from bot.alerts import _admin_user_id
    if _admin_user_id == 0:
        return

    try:
        stats = await db_usage.get_stats_summary()
        fb_stats = await db_feedback.get_feedback_stats()

        monthly_cost = await db_usage.get_monthly_cost()

        lines = [
            "📊 Resumen semanal del Oráculo",
            "",
            f"Total consultas: {stats['total_uses']}",
            f"Coste total: ${stats['total_cost']:.4f}",
            f"Coste mes actual: ${monthly_cost:.4f}",
            f"Cache hit rate: {stats['cache_rate']:.1f}%",
            f"Truncadas: {stats['truncated_count']}",
            "",
            "Top 5 usuarios:",
        ]
        for u in stats["top_users"]:
            lines.append(f"  {u['alias']}: {u['uses']} usos (${u['cost']:.4f})")

        lines.append("")
        lines.append("Por modo:")
        for m in stats["by_mode"]:
            lines.append(f"  {m['mode']}: {m['uses']}")

        lines.append("")
        lines.append(f"Feedback: 👍 {fb_stats['positive']} / 👎 {fb_stats['negative']}")

        text = "\n".join(lines)
        await context.bot.send_message(_admin_user_id, text)
    except Exception as e:
        logger.error(f"Error enviando resumen semanal: {e}")
