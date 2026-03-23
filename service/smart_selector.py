"""Selector inteligente de tirada por keywords. Sin API, coste cero.

Analiza la pregunta del usuario y devuelve la variante de tarot mas apropiada.
Solo usa patrones de texto en castellano.
"""

import re
import unicodedata

# Patrones si/no (pregunta directa con verbo interrogativo)
_YES_NO_VERBS = (
    "debería", "deberia", "debo", "puedo", "va a", "voy a",
    "es bueno", "es malo", "tengo que", "me conviene", "conviene",
    "será", "sera", "hay", "habrá", "habra", "puede", "es posible",
    "es cierto", "me quiere", "le gusto", "volverá", "volvera",
    "funcionará", "funcionara", "merece la pena", "vale la pena",
    "es verdad", "es mentira", "está bien", "esta bien",
)
_YES_NO_RE = re.compile(
    r"^¿?\s*(" + "|".join(re.escape(v) for v in _YES_NO_VERBS) + r")\b",
    re.IGNORECASE,
)
_YES_NO_PHRASES = {"sí o no", "si o no", "si/no", "sí/no"}

# Keywords temporales (evolucion, pasado/futuro, progreso)
_TEMPORAL_KEYWORDS = {
    "pasado", "futuro", "evolución", "evolucion", "evolucionar",
    "cómo va", "como va", "cómo irá", "como ira",
    "qué pasó", "que paso", "qué viene", "que viene",
    "hacia dónde", "hacia donde", "progreso", "camino",
    "antes y después", "antes y despues", "próximamente", "proximamente",
    "qué me espera", "que me espera", "tendencia",
}

# Keywords complejos (situacion, relacion, conflicto)
_COMPLEX_KEYWORDS = {
    "relación", "relacion", "situación", "situacion",
    "por qué", "por que", "qué está pasando", "que esta pasando",
    "qué pasa", "que pasa", "conflicto", "dilema",
    "problema", "bloqueo", "estancado", "estancada",
    "no avanzo", "no consigo", "qué hago", "que hago",
    "múltiples", "multiples", "complejo", "complicado",
}

_COMPLEX_WORD_THRESHOLD = 30  # >30 palabras → complejo


def _normalize(text: str) -> str:
    """Normaliza texto: strip, lowercase, espacios simples."""
    return " ".join(text.strip().lower().split())


def select_variant(question: str) -> str:
    """Analiza una pregunta y devuelve la variante de tarot recomendada.

    Returns:
        "1_carta" para si/no, "3_cartas" para temporal,
        "cruz_celta" para complejo, "3_cartas" por defecto.
    """
    if not question or not question.strip():
        return "3_cartas"

    q = _normalize(question)
    words = q.split()

    # Pregunta muy larga → compleja
    if len(words) > _COMPLEX_WORD_THRESHOLD:
        return "cruz_celta"

    # Si/No explícito
    for phrase in _YES_NO_PHRASES:
        if phrase in q:
            return "1_carta"

    # Si/No por verbo interrogativo
    if _YES_NO_RE.search(q):
        return "1_carta"

    # Temporal
    for kw in _TEMPORAL_KEYWORDS:
        if kw in q:
            return "3_cartas"

    # Complejo
    for kw in _COMPLEX_KEYWORDS:
        if kw in q:
            return "cruz_celta"

    # Default
    return "3_cartas"


# Labels para mensajes
_VARIANT_LABELS = {
    "1_carta": "Una carta",
    "3_cartas": "Tres cartas (Pasado-Presente-Futuro)",
    "cruz_celta": "Cruz Celta (10 cartas)",
    "herradura": "Herradura (7 cartas)",
    "relacion": "Relación (6 cartas)",
    "estrella": "Estrella (7 cartas)",
    "cruz_simple": "Cruz Simple (5 cartas)",
    "si_no": "Sí/No reforzado (3 cartas)",
    "tirada_dia": "Tirada del día (1 carta)",
}


def variant_label(variant: str) -> str:
    """Devuelve nombre legible de la variante."""
    return _VARIANT_LABELS.get(variant, variant)
