"""Handler de /start y /startoraculo.

Deep link routing para onboarding en DM:
  t.me/bot?start=onboarding → flujo de registro en privado
  t.me/bot?start=update_profile → actualizar perfil en privado
  t.me/bot?start=set_fullname → registrar nombre para numerologia en privado

Seguridad:
  - Whitelist estricta de parametros (sin regex, solo set de strings validos)
  - Rate limit: max 3 intentos de onboarding por user_id por hora
  - Cualquier parametro no reconocido → presentacion y nada mas
"""

import time
from collections import defaultdict

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from database import users as db_users

# Whitelist estricta de parametros de deep link validos
_VALID_START_PARAMS = {"onboarding", "update_profile", "set_fullname"}

# Rate limit para onboarding en DM: {user_id: [timestamps]}
_onboarding_attempts: dict[int, list[float]] = defaultdict(list)
_ONBOARDING_RATE_LIMIT = 3  # max intentos
_ONBOARDING_RATE_WINDOW = 3600  # 1 hora


def _check_onboarding_rate_limit(user_id: int) -> bool:
    """True si el usuario puede iniciar onboarding. False si excedio el limite."""
    now = time.time()
    # Limpiar intentos expirados
    _onboarding_attempts[user_id] = [
        t for t in _onboarding_attempts[user_id]
        if now - t < _ONBOARDING_RATE_WINDOW
    ]
    if len(_onboarding_attempts[user_id]) >= _ONBOARDING_RATE_LIMIT:
        return False
    _onboarding_attempts[user_id].append(now)
    return True


_INTRO_GROUP = """🔮 Soy El Pezuñento, el oráculo de La Taberna de los Sortilegios.

Leo las cartas, las runas, los hexagramas y lo que haga falta. No endulzo las lecturas y no hago recados. Si preguntas en serio, te respondo en serio.

Usa /consulta para presentarte y empezar. Si ya nos conocemos, escribe /tarot, /runa, /iching o lo que te apetezca."""

_INTRO_GROUP_REGISTERED = """🔮 Ya nos conocemos, {alias}.

Usa /tarot, /runa, /iching, /geomancia, /numerologia, /natal, /vedica, /oraculo, /bibliomancia o /ayudaoraculo para ver todo lo que puedo hacer."""

_INTRO_DM = """🔮 Soy El Pezuñento, el oráculo de La Taberna de los Sortilegios.

Solo funciono en el grupo. No hago consultas privadas. Búscame en La Taberna."""

_DM_RATE_LIMITED = "Demasiados intentos de registro. Espera un rato."


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /start y /startoraculo — DM o grupo.

    En DM con deep link valido → redirige al ConversationHandler correspondiente.
    En DM sin deep link → presentacion.
    En grupo → presentacion in-character.
    """
    chat = update.effective_chat
    user_id = update.effective_user.id

    if chat.type == "private":
        # Extraer parametro de deep link (si existe)
        args = context.args
        param = args[0] if args else None

        # Sanitizar: solo aceptar parametros de la whitelist
        if param and param not in _VALID_START_PARAMS:
            logger.warning(f"Deep link invalido de user {user_id}: {param!r}")
            param = None

        if param is None:
            # /start sin parametro en DM → presentacion
            await update.message.reply_text(_INTRO_DM)
            return

        # Deep link valido → verificar rate limit
        if not _check_onboarding_rate_limit(user_id):
            await update.message.reply_text(_DM_RATE_LIMITED)
            return

        # Guardar el parametro para que el ConversationHandler lo recoja
        context.user_data["dm_deep_link"] = param
        logger.info(f"Deep link DM: user={user_id}, param={param}")

        if param == "onboarding":
            # El ConversationHandler de DM onboarding lo recogera
            from bot.handlers.dm_onboarding import start_dm_onboarding
            await start_dm_onboarding(update, context)
            return

        if param == "update_profile":
            from bot.handlers.dm_onboarding import start_dm_update_profile
            await start_dm_update_profile(update, context)
            return

        if param == "set_fullname":
            from bot.handlers.dm_onboarding import start_dm_set_fullname
            await start_dm_set_fullname(update, context)
            return

        # Fallback (no deberia llegar aqui por la whitelist)
        await update.message.reply_text(_INTRO_DM)
        return

    # En grupo
    user = await db_users.get_user(user_id)

    if user and user["onboarding_complete"]:
        text = _INTRO_GROUP_REGISTERED.format(alias=user["alias"])
    else:
        text = _INTRO_GROUP

    await update.message.reply_text(
        text,
        reply_to_message_id=update.message.message_id,
    )
