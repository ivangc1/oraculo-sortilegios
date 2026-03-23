"""Sub-prompt de carta natal védica (Jyotish)."""


def get_sub_prompt() -> str:
    return _SUB_NATAL_VEDICA


_SUB_NATAL_VEDICA = """MODO: Carta natal védica (Jyotish, ayanamsa Lahiri).
Se proporcionan: Sol, Luna, Ascendente (signos siderales), nakshatra lunar,
planetas en signos y casas, dashas (Mahadasha/Antardasha), yogas principales.
Interpreta desde la tradición Jyotish: nakshatras, dashas, dignidades planetarias.
Lectura extensa — aprovecha el espacio."""
