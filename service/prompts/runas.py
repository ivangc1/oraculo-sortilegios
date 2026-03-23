"""Sub-prompts de runas (Elder Futhark)."""


def get_sub_prompt(variant: str) -> str:
    prompts = {
        "odin": _SUB_ODIN,
        "nornas": _SUB_NORNAS,
        "cruz": _SUB_CRUZ,
        "cinco": _SUB_CINCO,
        "siete": _SUB_SIETE,
    }
    return prompts.get(variant, "")


_SUB_ODIN = """MODO: Runas — Runa de Odin (1 runa).
Una sola runa del Elder Futhark. Respuesta directa y concentrada.
Interpreta su significado esencial y como aplica a la situacion del consultante.
Wyrd (runa en blanco) = potencial puro, destino no escrito.
Respuesta breve."""

_SUB_NORNAS = """MODO: Runas — Tres Nornas (3 runas).
Tres runas en posiciones: Urd (pasado/causa), Verdandi (presente/accion), Skuld (futuro/resultado).
Interpreta cada runa en su posicion y la narrativa que forman juntas."""

_SUB_CRUZ = """MODO: Runas — Cruz Runica (5 runas).
Cinco runas en cruz:
1. Centro: situacion presente
2. Izquierda: pasado/origen
3. Derecha: futuro/direccion
4. Arriba: influencia consciente
5. Abajo: influencia inconsciente

Interpreta todas las posiciones y sus relaciones."""

_SUB_CINCO = """MODO: Runas — Cinco Runas (5 runas).
Cinco runas en linea con posiciones:
1. Situacion — el estado actual de las cosas
2. Desafio — lo que enfrenta el consultante
3. Accion — lo que debe hacer
4. Sacrificio — lo que debe soltar o entregar
5. Resultado — hacia donde conduce el camino

Marco nordico. El sacrificio es clave: toda transformacion tiene un coste."""

_SUB_SIETE = """MODO: Runas — Siete Runas (7 runas).
Siete runas en linea con posiciones:
1. Pasado — origen de la situacion
2. Presente — estado actual
3. Futuro — hacia donde se dirige
4. Consejo — guia para actuar
5. Obstaculo — lo que se interpone
6. Ayuda — recursos, aliados, fuerzas a favor
7. Resultado — desenlace probable

Lectura extensa. La mas completa del sistema runico. Teje una narrativa con las 7 runas."""
