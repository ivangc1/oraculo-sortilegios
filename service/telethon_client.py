"""Cliente Telethon para acceso MTProto (admin log, etc.).

Usa StringSession (en memoria) para evitar archivos de sesion y locks SQLite.
Se conecta con bot_token, no cuenta de usuario.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from loguru import logger
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import (
    ChannelAdminLogEventActionChangePhoto,
    ChannelAdminLogEventActionChangeTitle,
    ChannelAdminLogEventActionDeleteMessage,
    ChannelAdminLogEventActionEditMessage,
    ChannelAdminLogEventActionParticipantInvite,
    ChannelAdminLogEventActionParticipantJoin,
    ChannelAdminLogEventActionParticipantLeave,
    ChannelAdminLogEventActionParticipantToggleAdmin,
    ChannelAdminLogEventActionParticipantToggleBan,
    ChannelAdminLogEventActionToggleInvites,
    ChannelAdminLogEventActionUpdatePinned,
)
from telethon.tl.types import ChannelAdminLogEventsFilter


@dataclass
class AdminLogEntry:
    """Entrada procesada del admin log."""
    date: datetime
    admin_name: str
    action: str
    target: str


# Mapeo de filtros usuario → kwargs para ChannelAdminLogEventsFilter
# Cada filtro activa solo los campos relevantes del filtro MTProto.
FILTER_MAP: dict[str, dict[str, bool]] = {
    "pin": {"pin": True, "unpin": True},
    "unpin": {"unpin": True},
    "ban": {"ban": True, "unban": True, "kick": True},
    "kick": {"kick": True},
    "invite": {"invite": True},
    "delete": {"delete": True},
    "edit": {"edit": True},
    "admin": {"promote": True, "demote": True},
    "title": {"info": True},
    "photo": {"info": True},
    "settings": {"settings": True},
}

VALID_FILTERS: list[str] = sorted(FILTER_MAP.keys())


def _get_user_display(user) -> str:
    """Nombre legible de un usuario Telethon."""
    if user is None:
        return "Desconocido"
    first = getattr(user, "first_name", None) or ""
    last = getattr(user, "last_name", None) or ""
    full = f"{first} {last}".strip()
    if full:
        return full
    user_id = getattr(user, "id", None)
    return f"User#{user_id}" if user_id else "Desconocido"


def _classify_action(event) -> tuple[str, str]:
    """Clasifica un evento de admin log en (accion, target).

    Returns:
        Tupla (etiqueta de accion, descripcion del objetivo)
    """
    action = event.action

    if isinstance(action, ChannelAdminLogEventActionUpdatePinned):
        msg = getattr(action, "message", None)
        if msg and getattr(msg, "message", None):
            preview = msg.message[:60] + ("..." if len(msg.message) > 60 else "")
            pinned = not getattr(msg, "pinned", True)
            label = "Desfijo mensaje" if pinned else "Fijo mensaje"
            return label, f'"{preview}"'
        return "Pin/Unpin", "(mensaje sin texto)"

    if isinstance(action, ChannelAdminLogEventActionDeleteMessage):
        msg = getattr(action, "message", None)
        if msg and getattr(msg, "message", None):
            preview = msg.message[:60] + ("..." if len(msg.message) > 60 else "")
            return "Borro mensaje", f'"{preview}"'
        return "Borro mensaje", "(sin preview)"

    if isinstance(action, ChannelAdminLogEventActionEditMessage):
        return "Edito mensaje", ""

    if isinstance(action, ChannelAdminLogEventActionParticipantToggleBan):
        target_user = getattr(action, "new_participant", None)
        if target_user:
            user = getattr(target_user, "user_id", None)
            return "Ban/Unban", f"User#{user}" if user else ""
        return "Ban/Unban", ""

    if isinstance(action, ChannelAdminLogEventActionParticipantToggleAdmin):
        return "Cambio admin", ""

    if isinstance(action, ChannelAdminLogEventActionParticipantInvite):
        return "Invito usuario", ""

    if isinstance(action, ChannelAdminLogEventActionParticipantJoin):
        return "Se unio", ""

    if isinstance(action, ChannelAdminLogEventActionParticipantLeave):
        return "Salio", ""

    if isinstance(action, ChannelAdminLogEventActionChangeTitle):
        new_title = getattr(action, "new_value", "")
        return "Cambio titulo", f'→ "{new_title}"'

    if isinstance(action, ChannelAdminLogEventActionChangePhoto):
        return "Cambio foto", ""

    if isinstance(action, ChannelAdminLogEventActionToggleInvites):
        return "Cambio invitaciones", ""

    # Fallback para acciones no mapeadas
    return type(action).__name__.replace("ChannelAdminLogEventAction", ""), ""


class TelethonClient:
    """Cliente Telethon para operaciones MTProto (admin log)."""

    def __init__(self, api_id: int, api_hash: str, bot_token: str):
        self._api_id = api_id
        self._api_hash = api_hash
        self._bot_token = bot_token
        self._client: TelegramClient | None = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected()

    async def connect(self) -> None:
        """Conecta el cliente Telethon con bot_token."""
        self._client = TelegramClient(
            StringSession(), self._api_id, self._api_hash
        )
        await self._client.start(bot_token=self._bot_token)
        logger.info("Telethon client conectado")

    async def disconnect(self) -> None:
        """Desconecta el cliente Telethon."""
        if self._client:
            await self._client.disconnect()
            self._client = None
            logger.info("Telethon client desconectado")

    async def get_admin_log(
        self,
        chat_id: int,
        filter_type: str | None = None,
        limit: int = 10,
    ) -> list[AdminLogEntry]:
        """Consulta el admin log de un grupo/canal.

        Args:
            chat_id: ID del chat (formato Bot API, ej: -1001234567890)
            filter_type: Filtro opcional (pin, ban, delete, edit, etc.)
            limit: Numero maximo de entradas a devolver

        Returns:
            Lista de AdminLogEntry ordenada por fecha descendente

        Raises:
            ConnectionError: Si el cliente no esta conectado
            ValueError: Si el filtro no es valido
            PermissionError: Si el bot no tiene permisos de admin
        """
        if not self.is_connected:
            raise ConnectionError("Telethon client no conectado")

        if filter_type is not None and filter_type not in FILTER_MAP:
            raise ValueError(f"Filtro invalido: {filter_type}")

        # Construir filtro MTProto
        events_filter = None
        if filter_type:
            filter_kwargs = FILTER_MAP[filter_type]
            # Todos los campos a False, luego activar los del filtro
            all_false = {k: False for k in (
                "join", "leave", "invite", "ban", "unban", "kick",
                "promote", "demote", "info", "settings", "pin", "unpin",
                "edit", "delete", "group_call",
            )}
            all_false.update(filter_kwargs)
            events_filter = ChannelAdminLogEventsFilter(**all_false)

        try:
            entity = await self._client.get_entity(chat_id)
        except Exception as e:
            raise PermissionError(f"No se pudo acceder al chat: {e}") from e

        entries: list[AdminLogEntry] = []
        try:
            async for event in self._client.iter_admin_log(
                entity, limit=limit, filter=events_filter,
            ):
                admin_name = _get_user_display(event.user)
                action_label, target = _classify_action(event)
                entries.append(AdminLogEntry(
                    date=event.date,
                    admin_name=admin_name,
                    action=action_label,
                    target=target,
                ))
        except Exception as e:
            error_msg = str(e).lower()
            if "admin" in error_msg or "right" in error_msg or "permission" in error_msg:
                raise PermissionError(f"Sin permisos de admin: {e}") from e
            raise

        return entries
