"""Sub-prompts de tarot (inyectados en user message)."""


def get_sub_prompt(variant: str) -> str:
    if variant == "1_carta":
        return _SUB_1_CARTA
    elif variant == "3_cartas":
        return _SUB_3_CARTAS
    elif variant == "cruz_celta":
        return _SUB_CRUZ_CELTA
    return ""


_SUB_1_CARTA = """MODO: Tarot — Una carta.
Tirada de una sola carta del Tarot Rider-Waite.
Si hay pregunta, interpreta como respuesta directa (sí/no con matices).
Si no hay pregunta, interpreta como mensaje del día o consejo general.
Respuesta breve y concentrada."""

_SUB_3_CARTAS = """MODO: Tarot — Tres cartas.
Tirada de tres cartas del Tarot Rider-Waite en posiciones: Pasado, Presente, Futuro.
Interpreta cada carta en su posición y luego la narrativa que forman juntas.
Si hay pregunta, toda la lectura gira alrededor de ella."""

_SUB_CRUZ_CELTA = """MODO: Tarot — Cruz Celta (10 cartas).
Disposición Waite clásica. Las 10 posiciones son:
1. Situación presente
2. Obstáculo/cruce (carta horizontal sobre la 1)
3. Base/fundamento
4. Pasado reciente
5. Corona/posibilidad
6. Futuro cercano
7. El consultante
8. Entorno/influencias externas
9. Esperanzas y miedos
10. Resultado final

Interpreta TODAS las posiciones. Relaciona las cartas entre sí.
Esta es la lectura más extensa — aprovecha el espacio."""
