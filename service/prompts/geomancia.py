"""Sub-prompts de geomancia."""


def get_sub_prompt(variant: str) -> str:
    if variant == "1_figura":
        return _SUB_1_FIGURA
    elif variant == "escudo":
        return _SUB_ESCUDO
    return ""


_SUB_1_FIGURA = """MODO: Geomancia — Una figura.
Una sola figura geomántica con sus atributos elementales y planetarios.
Interpreta su significado esencial y cómo aplica a la situación.
Respuesta breve y directa."""

_SUB_ESCUDO = """MODO: Geomancia — Escudo completo.
Escudo geomántico con:
- 4 Madres (generadas aleatoriamente)
- 4 Hijas (derivadas de las Madres)
- 4 Sobrinas (XOR par a par)
- 2 Testigos (XOR de Sobrinas)
- 1 Juez (XOR de Testigos)
- Reconciliador (XOR Juez + Primera Madre, si el Juez es ambiguo)

Interpreta la progresión completa del escudo. Las Madres representan el origen,
las Hijas el desarrollo, las Sobrinas la síntesis. Los Testigos son las fuerzas
en conflicto y el Juez la resolución.

Lectura extensa — aprovecha el espacio."""
