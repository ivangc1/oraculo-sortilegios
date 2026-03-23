"""Sub-prompts de numerología (pitagórica)."""


def get_sub_prompt(variant: str) -> str:
    if variant == "informe":
        return _SUB_INFORME
    elif variant == "compatibilidad":
        return _SUB_COMPATIBILIDAD
    return ""


_SUB_INFORME = """MODO: Numerología pitagórica — Informe completo.
Datos proporcionados: camino de vida, número de expresión, número del alma,
año personal, mes personal.
Interpreta cada número y cómo interactúan entre sí.
Si hay nombre completo de nacimiento disponible, se han usado para los cálculos."""

_SUB_COMPATIBILIDAD = """MODO: Numerología pitagórica — Compatibilidad.
Se proporcionan dos caminos de vida (solo fecha de nacimiento, no nombre).
Analiza la compatibilidad entre ambos números: armonías, tensiones, dinámicas.
No pidas más datos — trabaja solo con los caminos de vida dados."""
