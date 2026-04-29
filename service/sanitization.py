"""Saneo de texto antes de inyectarlo en el user_message del prompt LLM.

Cualquier campo que provenga de un usuario (alias, full_birth_name, birth_city,
question, etc.) se neutraliza para que no pueda forzar el cierre/apertura de
los tags estructurales del prompt:

  <instrucciones_modo>...</instrucciones_modo>
  <perfil_consultante>...</perfil_consultante>
  <tirada>...</tirada>
  <datos_extra>...</datos_extra>
  <pregunta>...</pregunta>
  <sin_pregunta>...</sin_pregunta>

Si un usuario consigue meter literalmente uno de estos tags en su input,
aquí se reemplazan los caracteres `<` y `>` por sus variantes Unicode `‹›`,
preservando legibilidad sin permitir que el modelo los interprete como
delimitadores estructurales.
"""

from __future__ import annotations

import re

_STRUCTURAL_TAGS = (
    "instrucciones_modo", "perfil_consultante", "tirada",
    "datos_extra", "pregunta", "sin_pregunta",
)
_TAG_PATTERN = re.compile(
    r"</?(" + "|".join(_STRUCTURAL_TAGS) + r")\s*>", re.IGNORECASE,
)


def sanitize_user_text(text: object) -> str:
    """Neutraliza tags estructurales en cualquier valor escalar.

    Acepta str, int, float, None, etc. (siempre devuelve str).
    """
    if text is None:
        return ""
    s = str(text)
    return _TAG_PATTERN.sub(
        lambda m: m.group(0).replace("<", "‹").replace(">", "›"),
        s,
    )
