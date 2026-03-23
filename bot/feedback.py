"""Handler de feedback: expiración 7d, anti-ajeno, anti-doble, tolerante a mensajes borrados."""

from datetime import datetime, timezone

from loguru import logger
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.config import Settings
from database import feedback as db_feedback
from database import usage as db_usage


async def handle_feedback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, settings: Settings
) -> None:
    """Procesa callback de feedback (fb:p:123 o fb:n:123)."""
    query = update.callback_query
    if query is None:
        return

    data = query.data
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "fb":
        await query.answer()
        return

    sentiment = parts[1]  # "p" o "n"
    try:
        usage_id = int(parts[2])
    except ValueError:
        await query.answer()
        return

    # Verificar existencia del usage
    usage = await db_usage.get_usage(usage_id)
    if not usage:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except BadRequest:
            pass  # Mensaje ya borrado
        await query.answer("Esta lectura ya no existe.", show_alert=False)
        return

    # Solo dueño
    if query.from_user.id != usage["user_id"]:
        await query.answer("Este feedback no es tuyo.", show_alert=False)
        return

    # Expiración
    usage_time = datetime.fromisoformat(usage["timestamp"])
    if usage_time.tzinfo is None:
        usage_time = usage_time.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - usage_time
    if age.days > settings.FEEDBACK_EXPIRY_DAYS:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except BadRequest:
            pass
        await query.answer("Feedback expirado.", show_alert=False)
        return

    # No doble
    existing = await db_feedback.get_feedback(usage_id)
    if existing:
        await query.answer("Ya diste tu opinión.", show_alert=False)
        return

    # Guardar y limpiar botones
    await db_feedback.save_feedback(usage_id, query.from_user.id, positive=(sentiment == "p"))
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except BadRequest:
        pass  # Tolerante a mensaje borrado
    await query.answer("Gracias ✨")
