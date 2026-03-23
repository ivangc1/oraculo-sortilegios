"""Sub-prompts de runas (Elder Futhark)."""


def get_sub_prompt(variant: str) -> str:
    if variant == "odin":
        return _SUB_ODIN
    elif variant == "nornas":
        return _SUB_NORNAS
    elif variant == "cruz":
        return _SUB_CRUZ
    return ""


_SUB_ODIN = """MODO: Runas — Runa de Odín (1 runa).
Una sola runa del Elder Futhark. Respuesta directa y concentrada.
Interpreta su significado esencial y cómo aplica a la situación del consultante.
Wyrd (runa en blanco) = potencial puro, destino no escrito.
Respuesta breve."""

_SUB_NORNAS = """MODO: Runas — Tres Nornas (3 runas).
Tres runas en posiciones: Urd (pasado/causa), Verdandi (presente/acción), Skuld (futuro/resultado).
Interpreta cada runa en su posición y la narrativa que forman juntas."""

_SUB_CRUZ = """MODO: Runas — Cruz Rúnica (5 runas).
Cinco runas en cruz:
1. Centro: situación presente
2. Izquierda: pasado/origen
3. Derecha: futuro/dirección
4. Arriba: influencia consciente
5. Abajo: influencia inconsciente

Interpreta todas las posiciones y sus relaciones."""
