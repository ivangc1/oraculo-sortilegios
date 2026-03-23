"""Sub-prompt de carta natal tropical."""


def get_sub_prompt() -> str:
    return _SUB_NATAL_TROPICAL


_SUB_NATAL_TROPICAL = """MODO: Carta natal tropical (Placidus).
Se proporcionan: Sol, Luna, Ascendente, planetas en signos y casas, aspectos principales.
Interpreta el mapa completo: la personalidad (Sol/Luna/Asc), las áreas de vida (casas),
las dinámicas (aspectos).
Si se usó Whole Sign en vez de Placidus (por latitud extrema), se indica en los datos.
Lectura extensa — aprovecha el espacio."""
