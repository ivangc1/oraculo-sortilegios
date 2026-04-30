"""Helpers para flags `*_awaiting_*` en context.user_data.

Cada handler que pide texto al usuario marca un flag con `time.time()` para
expirar a los 5 minutos. Si el usuario salta de un flujo a otro sin responder,
los flags antiguos quedan colgando en el pickle hasta expirar y pueden
confundir al dispatcher de texto. `clear_other_awaiting()` los borra al
arrancar un flujo nuevo.
"""

from typing import MutableMapping

# Lista única de flags pendientes de respuesta del usuario. Cualquier handler
# nuevo que añada un flag debe registrarlo aquí.
AWAITING_FLAGS = (
    "tarot_awaiting_question",
    "oraculo_awaiting_question",
    "numerologia_awaiting_name",
    "numerologia_awaiting_compat_date",
)


def clear_other_awaiting(user_data: MutableMapping, except_key: str | None = None) -> None:
    """Limpia todos los flags awaiting excepto el especificado.

    Llamar al inicio de cada handler que vaya a setear un flag de espera.
    Evita que un flag antiguo capture el texto del nuevo flujo.
    """
    for key in AWAITING_FLAGS:
        if key != except_key:
            user_data.pop(key, None)
