"""Entry point del bot. Signals, PicklePersistence, JobQueue, startup/shutdown."""

import asyncio
import pickle
import signal
import sys
import time
from datetime import time as dt_time
from pathlib import Path

from loguru import logger
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from bot.config import load_settings
from bot.alerts import set_admin_user_id, send_alert
from bot.concurrency import init_semaphore
from bot.feedback import handle_feedback
from bot.jobs import cleanup_membership_cache_job, send_weekly_summary
from bot.middleware import handle_migration
from database.connection import Database
from service.anthropic_client import AnthropicService
from service.interpreter import InterpreterService

# Timestamp de arranque
BOT_START_TIME = time.time()

# Configurar loguru
logger.remove()  # Eliminar handler default
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    level="DEBUG",
)
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    rotation="00:00",
    retention="30 days",
    compression="gz",
    level="INFO",
    backtrace=False,
    diagnose=False,
)


def create_persistence() -> PicklePersistence:
    """Crea PicklePersistence con protección contra corrupción."""
    pickle_path = "bot_persistence.pickle"
    try:
        persistence = PicklePersistence(
            filepath=pickle_path,
            update_interval=60,
        )
    except (pickle.UnpicklingError, EOFError, FileNotFoundError, Exception):
        logger.warning("Persistence corrupted or missing, starting fresh")
        Path(pickle_path).unlink(missing_ok=True)
        persistence = PicklePersistence(
            filepath=pickle_path,
            update_interval=60,
        )
    return persistence


async def post_init(application: Application) -> None:
    """Inicialización post-arranque: DB, servicios, alertas."""
    settings = application.bot_data["settings"]

    # Inicializar DB
    await Database.get()

    # Alerta de arranque
    await send_alert(
        application.bot,
        "restart",
        f"🔄 Bot reiniciado (v{settings.BOT_VERSION})",
        throttle_seconds=300,
    )

    logger.info(f"Bot iniciado (v{settings.BOT_VERSION}, env={settings.ENV})")


async def post_shutdown(application: Application) -> None:
    """Cleanup: cerrar DB y cliente Anthropic."""
    await Database.close()
    anthropic_service: AnthropicService | None = application.bot_data.get("anthropic_service")
    if anthropic_service:
        await anthropic_service.close()
    logger.info("Bot apagado correctamente")


async def error_handler(update: object, context) -> None:
    """Handler global de errores. Sin datos sensibles en logs."""
    logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Algo ha fallado por dentro. Inténtalo de nuevo.",
                reply_to_message_id=update.effective_message.message_id,
            )
        except Exception:
            pass


def main() -> None:
    """Punto de entrada principal."""
    settings = load_settings()

    # Admin para alertas
    set_admin_user_id(settings.ADMIN_USER_ID)

    # Semáforo de concurrencia API
    init_semaphore(settings.MAX_CONCURRENT_API)

    # Servicios
    anthropic_service = AnthropicService(settings)
    interpreter_service = InterpreterService(anthropic_service)

    # Persistence
    persistence = create_persistence()

    # Crear aplicación
    app = (
        ApplicationBuilder()
        .token(settings.BOT_TOKEN)
        .persistence(persistence)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Guardar en bot_data para acceso global
    app.bot_data["settings"] = settings
    app.bot_data["anthropic_service"] = anthropic_service
    app.bot_data["interpreter_service"] = interpreter_service

    # === HANDLERS (orden importa: ConversationHandlers primero) ===

    # 1. Migración grupo → supergrupo (máxima prioridad)
    app.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE, handle_migration))

    # 2. ConversationHandlers (onboarding grupo + DM + actualizar perfil)
    from bot.handlers.onboarding import build_onboarding_handler
    from bot.handlers.dm_onboarding import build_dm_onboarding_handler
    from bot.handlers.profile import build_update_profile_handler
    app.add_handler(build_dm_onboarding_handler())  # DM primero (mas especifico)
    app.add_handler(build_onboarding_handler())     # Grupo
    app.add_handler(build_update_profile_handler())

    # 3. Comandos simples
    from bot.handlers.start import start_command
    from bot.handlers.help import help_command
    from bot.handlers.profile import miperfil_command, borrarme_command
    from bot.handlers.admin import stats_command, version_command
    from bot.handlers.tarot import tarot_command
    from bot.handlers.runas import runas_command
    from bot.handlers.iching import iching_command
    from bot.handlers.geomancia import geomancia_command
    from bot.handlers.numerologia import numerologia_command
    from bot.handlers.natal import natal_command, vedica_command
    from bot.handlers.oraculo import oraculo_command
    from bot.handlers.bibliomancia import bibliomancia_command
    from bot.handlers.admins import admins_command

    app.add_handler(CommandHandler("start", start_command))  # Deep links + DM
    app.add_handler(CommandHandler("startoraculo", start_command))
    app.add_handler(CommandHandler("ayudaoraculo", help_command))
    app.add_handler(CommandHandler("miperfil", miperfil_command))
    app.add_handler(CommandHandler("borrarme", borrarme_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("version", version_command))
    app.add_handler(CommandHandler("tarot", tarot_command))
    app.add_handler(CommandHandler("runa", runas_command))
    app.add_handler(CommandHandler("iching", iching_command))
    app.add_handler(CommandHandler("geomancia", geomancia_command))
    app.add_handler(CommandHandler("numerologia", numerologia_command))
    app.add_handler(CommandHandler("natal", natal_command))
    app.add_handler(CommandHandler("vedica", vedica_command))
    app.add_handler(CommandHandler("oraculo", oraculo_command))
    app.add_handler(CommandHandler("bibliomancia", bibliomancia_command))
    app.add_handler(CommandHandler("admins", admins_command))

    # 4. Callback handlers para modos con menú inline
    from bot.handlers.tarot import tarot_callback, tarot_question_callback, tarot_question_text, tarot_smart_callback
    from bot.handlers.runas import runas_execute
    from bot.handlers.iching import iching_execute
    from bot.handlers.geomancia import geomancia_execute
    from bot.handlers.numerologia import (
        numerologia_informe_callback, numerologia_compat_callback,
        numerologia_name_text, numerologia_compat_date_text,
    )
    from bot.handlers.natal import natal_callback
    from bot.handlers.oraculo import oraculo_question_text
    from bot.handlers.bibliomancia import bibliomancia_callback
    from bot.handlers.admins import admins_callback

    # Dispatcher de callbacks por prefijo
    async def dispatch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query or not query.data:
            return

        data = query.data

        # Feedback
        if data.startswith("fb:"):
            await handle_feedback(update, context, settings)
            return

        # Tarot sub-menus (must be before t: prefix check)
        if data.startswith("tm:"):
            from bot.keyboards import (
                tarot_keyboard, tarot_rapidas_keyboard,
                tarot_completas_keyboard, tarot_especiales_keyboard,
            )
            sub_map = {
                "tm:r": ("⚡ Tiradas rápidas:", tarot_rapidas_keyboard),
                "tm:c": ("🔮 Tiradas completas:", tarot_completas_keyboard),
                "tm:e": ("✨ Tiradas especiales:", tarot_especiales_keyboard),
                "tm:bk": ("Elige tu tirada:", tarot_keyboard),
            }
            entry = sub_map.get(data)
            if entry:
                text, kb_fn = entry
                try:
                    await query.edit_message_text(text, reply_markup=kb_fn())
                except Exception:
                    pass
            return

        # Tarot
        if data.startswith("t:"):
            variant_map = {
                "t:1": "1_carta", "t:3": "3_cartas", "t:cc": "cruz_celta",
                "t:hr": "herradura", "t:rl": "relacion", "t:es": "estrella",
                "t:cs": "cruz_simple", "t:sn": "si_no",
            }
            variant = variant_map.get(data)
            if variant:
                await tarot_callback(update, context, variant)
                return
            # Tirada del dia (sin pregunta)
            if data == "t:dd":
                await tarot_callback(update, context, "tirada_dia", skip_question=True)
                return
            # Smart selector
            if data == "t:sm":
                await tarot_smart_callback(update, context)
                return
            return

        # Pregunta si/no (para tarot y otros modos)
        if data == "q:y":
            await tarot_question_callback(update, context, "yes")
            return
        if data == "q:n":
            await tarot_question_callback(update, context, "no")
            return

        # Runas
        if data.startswith("r:"):
            variant_map = {"r:1": "odin", "r:3": "nornas", "r:cr": "cruz", "r:5": "cinco", "r:7": "siete"}
            variant = variant_map.get(data)
            if variant:
                await runas_execute(update, context, variant)
            return

        # I Ching
        if data == "ic":
            await iching_execute(update, context)
            return

        # Geomancia
        if data.startswith("g:"):
            variant_map = {"g:1": "1_figura", "g:e": "escudo"}
            variant = variant_map.get(data)
            if variant:
                await geomancia_execute(update, context, variant)
            return

        # Numerologia
        if data == "n:i":
            await numerologia_informe_callback(update, context)
            return
        if data == "n:c":
            await numerologia_compat_callback(update, context)
            return

        # Natal
        if data == "nt":
            await natal_callback(update, context, "tropical")
            return
        if data == "nv":
            await natal_callback(update, context, "vedica")
            return

        # Oraculo
        if data == "or":
            # Oraculo via callback (redirige al flujo ForceReply)
            await query.answer()
            return

        # Bibliomancia
        if data.startswith("bl:"):
            key_map = {"bl:bi": "biblia", "bl:co": "coran", "bl:gi": "gita", "bl:ev": "evangelio"}
            text_key = key_map.get(data)
            if text_key:
                await bibliomancia_callback(update, context, text_key)
            return

        # Admins
        if data.startswith("a:"):
            suffix = data[2:]
            if suffix == "bk":
                await admins_callback(update, context, "back")
            else:
                await admins_callback(update, context, suffix)
            return

    app.add_handler(CallbackQueryHandler(dispatch_callback))

    # 5. Handlers de texto libre (ForceReply responses)
    # Estos capturan respuestas a ForceReply de numerologia y oraculo
    async def dispatch_text_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Despacha texto libre a handlers que esperan ForceReply."""
        if context.user_data.get("tarot_awaiting_question"):
            await tarot_question_text(update, context)
            return
        if context.user_data.get("oraculo_awaiting_question"):
            await oraculo_question_text(update, context)
            return
        if context.user_data.get("numerologia_awaiting_name"):
            await numerologia_name_text(update, context)
            return
        if context.user_data.get("numerologia_awaiting_compat_date"):
            await numerologia_compat_date_text(update, context)
            return

    # Solo respuestas a mensajes del bot (reply)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.REPLY,
        dispatch_text_reply,
    ))

    # Error handler
    app.add_error_handler(error_handler)

    # JobQueue
    app.job_queue.run_repeating(
        cleanup_membership_cache_job, interval=3600, first=60
    )
    app.job_queue.run_daily(
        send_weekly_summary, time=dt_time(hour=9, minute=0), days=(0,)
    )

    # Crear directorio de logs si no existe
    Path("logs").mkdir(exist_ok=True)

    # Arrancar (long polling para desarrollo)
    logger.info("Arrancando bot (long polling)...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
