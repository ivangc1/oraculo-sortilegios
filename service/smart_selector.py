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
    "llegará", "llegara", "saldrá", "saldra", "terminará", "terminara",
    "pasará", "pasara", "resultará", "resultara", "mejorará", "mejorara",
    "cambiará", "cambiara", "le importo", "me perdonará", "me perdonara",
    "me buscará", "me buscara", "me llamará", "me llamara",
    "me escribirá", "me escribira", "es el momento", "es buena idea",
    "debería de", "deberia de", "lograré", "lograre", "conseguiré", "conseguire",
    "superaré", "superare", "saldrá bien", "saldra bien", "irá bien", "ira bien",
    "tiene futuro", "tiene sentido", "es compatible", "somos compatibles",
    "me conviene", "me perjudica", "es para mí", "es para mi",
    "es hora de", "hay posibilidad", "hay esperanza", "hay salida",
    "hay solución", "hay solucion", "tiene solución", "tiene solucion",
    "me valora", "me extraña", "me extrana", "me respeta",
    "me rechazará", "me rechazara", "me aceptará", "me aceptara",
    "me hace bien", "me hace daño", "me hace dano",
    "es definitivo", "es permanente", "es temporal", "es recíproco", "es reciproco",
    "lo conseguiré", "lo conseguire", "lo lograré", "lo lograre",
    "es mi culpa", "tengo razón", "tengo razon", "lo merece", "me merece",
    "volveré", "volvere",
    "me ama", "me odia", "me ignora", "me necesita", "me echa de menos",
    "es el indicado", "es la indicada", "es mi persona",
    "debo confiar", "puedo fiarme", "es de fiar",
    "tiene arreglo", "tiene remedio", "tiene cura",
    "acabará bien", "acabara bien", "acabará mal", "acabara mal",
    "saldré adelante", "saldre adelante", "se resolverá", "se resolvera",
    "continuará", "continuara", "habrá cambio", "habra cambio",
    "debo esperar", "debo soltar", "debo seguir", "debo dejarlo",
    "estoy haciendo bien", "lo estoy haciendo mal",
    "soy suficiente", "soy capaz", "tengo oportunidad",
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
    "hacia dónde", "hacia donde", "progreso", "mi camino",
    "antes y después", "antes y despues", "próximamente", "proximamente",
    "qué me espera", "que me espera", "tendencia",
    "a corto plazo", "a largo plazo", "próximos meses", "proximos meses",
    "próximo año", "proximo año", "esta semana", "este mes", "este año",
    "qué pasará", "que pasara", "cómo terminará", "como terminara",
    "cómo acabará", "como acabara", "desenlace", "trayectoria",
    "con el tiempo", "a futuro", "venidero", "resultado final",
    "qué será", "que sera", "adónde", "adonde", "dónde estaré", "donde estare",
    "cómo evolucionará", "como evolucionara", "cómo irá", "como ira",
    "en el futuro", "qué pasará con", "que pasara con",
    "qué me depara", "que me depara", "qué me aguarda", "que me aguarda",
    "siguiente paso", "próxima etapa", "proxima etapa", "nueva etapa",
    "qué sigue", "que sigue", "qué vendrá", "que vendra",
    "cómo continuará", "como continuara", "qué va a pasar", "que va a pasar",
    "ciclo", "nueva fase", "nueva etapa",
    "qué me traerá", "que me traera", "qué esperar", "que esperar",
    "en los próximos", "en los proximos", "esta temporada", "esta etapa",
    "rumbo", "dirección de", "en breve", "avance", "periodo", "período",
}

# Keywords complejos (situacion, relacion, conflicto, decisiones, camino)
_COMPLEX_KEYWORDS = {
    "relación", "relacion", "situación", "situacion",
    "por qué", "por que", "qué está pasando", "que esta pasando",
    "qué pasa", "que pasa", "conflicto", "dilema",
    "problema", "bloqueo", "estancado", "estancada",
    "no avanzo", "no consigo", "qué hago", "que hago",
    "múltiples", "multiples", "complejo", "complicado",
    # Preguntas de camino/proceso (cómo llegar a algo)
    "cómo llego", "como llego", "cómo llegar", "como llegar",
    "cómo puedo", "como puedo", "cómo lograr", "como lograr",
    "cómo conseguir", "como conseguir", "cómo superar", "como superar",
    "cómo salir", "como salir", "cómo afrontar", "como afrontar",
    "cómo mejorar", "como mejorar", "cómo manejar", "como manejar",
    "cómo hacer", "como hacer", "cómo saber", "como saber",
    "cómo cambiar", "como cambiar", "cómo avanzar", "como avanzar",
    "cómo resolver", "como resolver", "cómo encontrar", "como encontrar",
    "cómo enfrentar", "como enfrentar", "cómo lidiar", "como lidiar",
    # Necesidades y carencias
    "qué necesito", "que necesito", "qué me falta", "que me falta",
    "qué me impide", "que me impide", "qué me bloquea", "que me bloquea",
    "qué me frena", "que me frena", "qué me retiene", "que me retiene",
    "qué debo", "que debo", "qué debería", "que deberia",
    # Decisiones y elecciones
    "decisión", "decision", "elegir", "elección", "eleccion",
    "qué camino", "que camino", "qué opción", "que opcion",
    "encrucijada", "por dónde", "por donde", "alternativas",
    "me quedo o", "sigo o", "acepto o", "cambio o",
    # Relaciones y personas
    "con él", "con ella", "con ellos", "con mi pareja",
    "con mi ex", "con mi familia", "con mi jefe", "con mi amigo",
    "ruptura", "separación", "separacion", "reconciliación", "reconciliacion",
    "infidelidad", "traición", "traicion", "alejamiento",
    # Crisis y transformación
    "crisis", "transformación", "transformacion", "cambio de vida",
    "pérdida", "perdida", "duelo", "trauma", "miedo profundo",
    "propósito", "proposito", "misión de vida", "mision de vida",
    "vocación", "vocacion", "destino", "karma",
    "qué me enseña", "que me ensena", "lección", "leccion",
    # Trabajo y proyectos
    "trabajo o", "empleo", "proyecto", "negocio", "empresa",
    "contrato", "mudanza", "inversión", "inversion",
    "oportunidad", "oferta", "entrevista",
    # Salud emocional y bienestar
    "tóxico", "toxico", "relación tóxica", "persona tóxica",
    "sanar", "sanación", "sanacion", "herida", "heridas",
    "autoestima", "autoconocimiento", "autoconfianza",
    "me siento atrapado", "me siento atrapada",
    "estoy perdido", "estoy perdida", "no encuentro salida",
    "no sé qué hacer", "no se que hacer", "no entiendo qué", "no entiendo que",
    "miedo a", "tengo miedo de", "me da miedo",
    "soledad", "me siento solo", "me siento sola",
    "depresión", "depresion", "ansiedad crónica", "ansiedad cronica",
    # Vida y propósito profundo
    "qué hacer con mi vida", "que hacer con mi vida",
    "sentido de mi vida", "sentido de la vida", "sin sentido",
    "identidad", "quién soy", "quien soy",
    "entre dos", "dos personas", "dos opciones", "dos caminos",
    "a quién", "a quien", "a cuál", "a cual",
    "orientación", "orientacion", "consejo", "guía", "guia",
    "límites", "limites", "poner límites", "poner limites",
    "manipulación", "manipulacion", "control", "dependencia",
    # Más formas de preguntar "cómo"
    "cómo dejar", "como dejar", "cómo soltar", "como soltar",
    "cómo perdonar", "como perdonar", "cómo comunicar", "como comunicar",
    "cómo recuperar", "como recuperar", "cómo proteger", "como proteger",
    "cómo conectar", "como conectar", "cómo atraer", "como atraer",
    "cómo reconquistar", "como reconquistar", "cómo alejar", "como alejar",
    # Situaciones vitales concretas
    "divorcio", "enfermedad", "diagnóstico", "diagnostico",
    "adicción", "adiccion", "deuda", "quiebra",
    "acoso", "maltrato", "abuso",
    "muerte", "fallecimiento", "luto", "duelo por",
    "embarazo", "fertilidad", "maternidad", "paternidad",
    "emigrar", "inmigrar", "extranjero", "mudanza al",
    "oposición", "oposicion", "examen importante", "beca",
    "pleito", "juicio", "demanda", "legal",
    "herencia", "testamento", "custodia",
    # Estados emocionales que merecen profundidad
    "rabia", "resentimiento", "rencor",
    "celos", "envidia",
    "decepción", "decepcion", "desilusión", "desilusión",
    "traicionado", "traicionada", "abandonado", "abandonada",
    "rechazado", "rechazada", "incomprendido", "incomprendida",
    "confundido", "confundida", "estoy confuso", "estoy confusa",
    "me cuesta", "me resulta difícil", "me resulta dificil",
    "estoy pasando por", "estoy viviendo",
    "necesito entender", "no comprendo por qué", "no comprendo por que",
    # Espiritualidad y energía
    "energía", "energia", "bloqueo energético", "bloqueo energetico",
    "vidas pasadas", "vida anterior", "misión del alma", "mision del alma",
    "contrato espiritual", "corte de lazos",
    "aura", "vibración", "vibracion",
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
