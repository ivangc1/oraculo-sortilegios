"""Sub-prompts de tarot (inyectados en user message).

Soporte multi-mazo: el parámetro deck ajusta la nomenclatura y enfoque interpretativo.
"""

_DECK_LABELS = {
    "rws": "Rider-Waite-Smith",
    "marsella": "Tarot de Marsella",
}

_MARSELLA_ADDENDUM = """
MAZO: Tarot de Marsella.
Nomenclatura Marsella: La Papisa (II), La Emperatriz (III), El Emperador (IV), El Papa (V),
El Enamorado (VI), El Arcano sin Nombre (XIII, sin nombrar como "La Muerte"),
La Casa de Dios (XVI, no "La Torre"), El Juicio (XX), El Mundo (XXI), El Loco (sin número).
Los Arcanos Menores del Marsella NO tienen escenas ilustradas — son patrones geométricos de palos.
La interpretación se basa más en numerología del palo y dignidad posicional que en imágenes narrativas.
Interpreta con la tradición marsellesa: más esencial, menos psicológica, más directa."""


def get_sub_prompt(variant: str, deck: str = "rws") -> str:
    prompts = {
        "1_carta": _SUB_1_CARTA,
        "3_cartas": _SUB_3_CARTAS,
        "cruz_celta": _SUB_CRUZ_CELTA,
        "herradura": _SUB_HERRADURA,
        "relacion": _SUB_RELACION,
        "estrella": _SUB_ESTRELLA,
        "cruz_simple": _SUB_CRUZ_SIMPLE,
        "si_no": _SUB_SI_NO,
        "tirada_dia": _SUB_TIRADA_DIA,
    }
    base = prompts.get(variant, "")
    if not base:
        return ""

    # Reemplazar referencias al mazo según deck
    if deck == "marsella":
        deck_label = _DECK_LABELS["marsella"]
        base = base.replace("del Tarot Rider-Waite", f"del {deck_label}")
        base = base.replace("Tarot Rider-Waite", deck_label)
        base = base.replace("Rider-Waite", deck_label)
        base = base.replace("Waite clasica", f"{deck_label} clasica")

    if deck == "marsella":
        base += _MARSELLA_ADDENDUM

    return base


_SUB_1_CARTA = """MODO: Tarot — Una carta.
Tirada de una sola carta del Tarot Rider-Waite.
Si hay pregunta, interpreta como respuesta directa (si/no con matices).
Si no hay pregunta, interpreta como mensaje del dia o consejo general.
Respuesta breve y concentrada."""

_SUB_3_CARTAS = """MODO: Tarot — Tres cartas.
Tirada de tres cartas del Tarot Rider-Waite en posiciones: Pasado, Presente, Futuro.
Interpreta cada carta en su posicion y luego la narrativa que forman juntas.
Si hay pregunta, toda la lectura gira alrededor de ella."""

_SUB_CRUZ_CELTA = """MODO: Tarot — Cruz Celta (10 cartas).
Disposicion Waite clasica. Las 10 posiciones son:
1. Situacion presente
2. Obstaculo/cruce (carta horizontal sobre la 1)
3. Base/fundamento
4. Pasado reciente
5. Corona/posibilidad
6. Futuro cercano
7. El consultante
8. Entorno/influencias externas
9. Esperanzas y miedos
10. Resultado final

Interpreta TODAS las posiciones. Relaciona las cartas entre si.
Esta es la lectura mas extensa — aprovecha el espacio."""

_SUB_HERRADURA = """MODO: Tarot — Herradura (7 cartas).
Tirada en arco de 7 cartas del Tarot Rider-Waite. Posiciones:
1. Pasado — lo que quedo atras e influye
2. Presente — situacion actual
3. Futuro — hacia donde se dirige
4. Consejo — que hacer al respecto
5. Entorno — influencias externas, personas, circunstancias
6. Esperanzas y miedos — lo que el consultante teme o desea
7. Resultado — desenlace probable

Lectura extensa. Interpreta todas las posiciones y teje una narrativa coherente."""

_SUB_RELACION = """MODO: Tarot — Relacion (6 cartas).
Tirada de 6 cartas centrada en la dinamica entre dos personas. Posiciones:
1. Yo — como esta el consultante en la relacion
2. La otra persona — como esta la otra parte
3. La relacion — estado actual del vinculo
4. Que nos une — lo que fortalece la conexion
5. Que nos separa — lo que genera distancia o conflicto
6. Consejo — como mejorar o resolver

Enfocate en la dinamica relacional. Sé directo sobre tensiones y fortalezas."""

_SUB_ESTRELLA = """MODO: Tarot — Estrella (7 cartas).
Tirada en forma de hexagrama (estrella de seis puntas) con carta central de sintesis. Posiciones:
1. Deseo — lo que el consultante quiere realmente
2. Obstaculo — lo que se interpone
3. Pasado — influencia de lo que fue
4. Futuro — hacia donde apunta la energia
5. Consciente — lo que el consultante sabe o reconoce
6. Inconsciente — lo que no ve, lo oculto, la sombra
7. Sintesis — la carta que integra todo, el mensaje central

Explora las capas conscientes e inconscientes. La carta de Sintesis cierra la lectura unificando los opuestos."""

_SUB_CRUZ_SIMPLE = """MODO: Tarot — Cruz Simple (5 cartas).
Tirada en forma de cruz con 5 cartas del Tarot Rider-Waite. Posiciones:
1. Tema central — el nucleo de la cuestion
2. Pasado — lo que influye desde atras
3. Futuro — lo que viene
4. Consciente — lo que el consultante percibe
5. Inconsciente — lo que no ve

Lectura equilibrada. Mas profunda que 3 cartas, mas enfocada que Cruz Celta."""

_SUB_SI_NO = """MODO: Tarot — Si/No reforzado (3 cartas).
Tirada de 3 cartas para preguntas directas. Posiciones:
1. Contexto — la situacion alrededor de la pregunta
2. Obstaculo — lo que dificulta o complica
3. Respuesta — la direccion que senalan las cartas

La carta de Respuesta da el si o no con matices. No seas ambiguo: da una respuesta clara y luego matizala.
Arcanos Mayores al derecho = si fuerte. Invertidos = no o con condiciones. Menores = depende del palo y numero."""

_SUB_TIRADA_DIA = """MODO: Tarot — Tirada del dia (1 carta).
Una sola carta como energia o tema del dia. NO hay pregunta.
Interpreta como la energia que acompana al consultante hoy.
Tono proactivo: que puede aprovechar, que debe vigilar.
Breve, directo, practico. No es una lectura profunda — es un flash de orientacion."""
