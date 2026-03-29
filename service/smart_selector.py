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
    "está enamorado", "esta enamorado", "está enamorada", "esta enamorada",
    "me engaña", "me miente", "me piensa", "me olvida",
    "le intereso", "me sigue queriendo", "me sigue amando",
    "es honesto", "es honesta", "es sincero", "es sincera",
    "es buena persona", "es mala persona",
    "lo hice bien", "lo hice mal", "es lo correcto",
    "debo preocuparme", "es peligroso", "es seguro",
    "es una señal", "lo supero", "lo superaré", "lo superare",
    "me afecta", "me arrepiento", "confía en mí", "confia en mi",
    "hay manera", "hay forma", "hay modo", "existe alguna forma",
    "dará resultado", "dara resultado", "vale la pena esperar",
    "me atrevo", "es demasiado tarde", "tengo tiempo", "importa realmente",
    "le digo", "le cuento", "le hablo", "se lo digo", "se lo cuento",
    "debo contarle", "debo decirle",
    "siente algo", "siente algo por mí", "siente algo por mi",
    "hay algo entre", "hay futuro entre", "somos buena pareja",
    "funcionamos", "funcionaremos", "estaré bien", "estare bien",
    "me busca", "me busca de verdad", "estoy equivocado", "estoy equivocada",
    "es culpa mía", "es culpa mia", "fue mi culpa",
    "merezco más", "merezco mejor", "merezco esto",
    "es normal lo que siento", "es real lo que siento",
    "tomé la decisión correcta", "tome la decision correcta",
    "haría bien", "haria bien", "estaría bien", "estaria bien",
    "encontraré", "encontrare", "conoceré", "conocere",
    "me casaré", "me casare", "tendré hijos", "tendre hijos",
    "me mudaré", "me mudare", "aprobaré", "aprobare",
    "ganaré", "ganare", "perderé", "perdere",
    "me curaré", "me curare", "durará", "durara",
    "estaremos juntos", "seguiremos juntos", "saldré de esta", "saldre de esta",
    "está con otra", "esta con otra", "está con otro", "esta con otro",
    "hay alguien más", "hay alguien mas", "hay otra persona",
    "me están usando", "me estan usando", "me están mintiendo", "me estan mintiendo",
    "seré feliz", "sere feliz", "soy feliz", "sobreviviré", "sobrevivire",
    "es normal", "es raro", "es una buena señal", "es mala señal",
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
    "cuándo cambia", "cuando cambia", "cuándo mejora", "cuando mejora",
    "cuándo acaba", "cuando acaba", "cuándo llega", "cuando llega",
    "para cuándo", "para cuando", "cuánto tiempo", "cuanto tiempo",
    "perspectivas", "perspectiva", "horizonte", "pronóstico", "pronostico",
    "evolución de", "evolucion de", "últimamente", "ultimamente",
    "a partir de ahora", "desde ahora",
    "dentro de poco", "tarde o temprano", "cuándo será", "cuando sera",
    "en qué momento", "en que momento", "cuándo cambiará", "cuando cambiara",
    "qué cambiará", "que cambiara", "hacia dónde voy", "hacia donde voy",
    "cómo acaba", "como acaba", "adónde lleva", "adonde lleva",
    "fin de", "comienzo de", "inicio de",
    "próximas semanas", "proximas semanas", "los próximos días", "los proximos dias",
    "este verano", "este otoño", "este otono", "este invierno", "esta primavera",
    "en navidad", "en navidades", "para fin de año", "para fin de ano",
    "cómo irá el año", "como ira el año", "como ira el ano",
    "qué trae este año", "que trae este ano", "qué trae este mes", "que trae este mes",
    "cómo sale todo", "como sale todo", "cómo resulta", "como resulta",
    "hay luz al final", "antes de que acabe", "antes de que termine",
    "cuándo voy a", "cuando voy a", "cuándo podré", "cuando podre",
    "cuándo encontraré", "cuando encontrare",
    "la semana que viene", "el mes que viene", "el año que viene",
    "en enero", "en febrero", "en marzo", "en abril", "en mayo",
    "en junio", "en julio", "en agosto", "en septiembre",
    "en octubre", "en noviembre", "en diciembre",
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
    # Más formas de "cómo"
    "cómo ganar", "como ganar", "cómo negociar", "como negociar",
    "cómo convencer", "como convencer", "cómo seducir", "como seducir",
    "cómo hablar con", "como hablar con", "cómo acercarme", "como acercarme",
    "cómo aproximarme", "como aproximarme", "cómo conquistar", "como conquistar",
    # Estados emocionales adicionales
    "frustración", "frustracion", "frustrado", "frustrada",
    "agotado", "agotada", "agotamiento", "burnout",
    "harto", "harta", "hartazgo",
    "inseguro", "insegura", "inseguridad",
    "vergüenza", "verguenza", "culpabilidad",
    "angustia", "desesperación", "desesperacion",
    "pánico", "panico", "desamor",
    # Personas y vínculos
    "con mi amigo", "con mi amiga", "con mi hermano", "con mi hermana",
    "con mi madre", "con mi padre", "con mis padres", "con mis hijos",
    "con mi hijo", "con mi hija", "con mi suegra", "con mi suegro",
    "ex novio", "ex novia", "ex marido", "ex mujer", "ex pareja",
    "nueva pareja", "nueva relación", "nueva relacion",
    "triángulo amoroso", "triangulo amoroso", "tercera persona",
    # Transiciones laborales y vitales
    "emprender", "autónomo", "autonomo", "freelance",
    "ascenso", "promoción laboral", "promocion laboral",
    "despido", "me echan", "me despiden",
    "renuncia", "dejar el trabajo", "cambio de trabajo",
    "jubilación", "jubilacion", "retiro profesional",
    "estudios", "carrera universitaria", "universidad",
    # Preguntas de interpretación/mensaje
    "qué mensaje", "que mensaje", "qué señal", "que senal",
    "qué simboliza", "que simboliza", "qué representa", "que representa",
    "qué me revela", "que me revela", "qué me indica", "que me indica",
    "qué me dice sobre", "que me dice sobre",
    # Más "cómo" internos y de crecimiento
    "cómo liberarme", "como liberarme", "cómo confiar", "como confiar",
    "cómo aceptar", "como aceptar", "cómo crecer", "como crecer",
    "cómo sanar mi", "como sanar mi", "cómo fluir", "como fluir",
    "cómo amar", "como amar", "cómo perderle", "como perderle",
    "cómo olvidar", "como olvidar", "cómo reinventarme", "como reinventarme",
    # Crisis específicas
    "crisis existencial", "crisis espiritual", "crisis de fe",
    "crisis de identidad", "crisis de pareja", "crisis vocacional",
    "proceso de duelo", "recaída", "recaida", "perfeccionismo",
    "procrastinación", "procrastinacion",
    # Relaciones en situaciones especiales
    "amor a distancia", "relación a distancia", "relacion a distancia",
    "relación abierta", "relacion abierta", "poligamia",
    "acoso laboral", "mobbing", "jefe tóxico", "jefe toxico",
    "ambiente laboral", "compañero difícil", "companero dificil",
    "reinventarme", "cambio de carrera", "cambio de profesión", "cambio de profesion",
    # Salud
    "recuperación", "recuperacion", "tratamiento", "cirugía", "cirugia",
    "operación", "operacion", "salud mental", "terapia",
    # Finanzas concretas
    "hipoteca", "alquiler", "ahorro", "ahorros",
    "crisis económica", "crisis economica", "situación económica", "situacion economica",
    # Esotérico específico
    "ley de atracción", "ley de atraccion", "manifestación", "manifestacion",
    "mal de ojo", "envidia ajena", "hechizo", "ritual", "magia",
    "brujería", "brujeria", "maldición", "maldicion",
    "protección espiritual", "proteccion espiritual",
    "señales del universo", "senales del universo",
    "sueños recurrentes", "suenos recurrentes",
    "sincronías", "sinconias", "ángel guardián", "angel guardian",
    # Más "cómo" de gestión y adaptación
    "cómo gestionar", "como gestionar", "cómo equilibrar", "como equilibrar",
    "cómo priorizar", "como priorizar", "cómo adaptarme", "como adaptarme",
    "cómo empezar de nuevo", "como empezar de nuevo", "cómo empezar", "como empezar",
    "cómo cerrar", "como cerrar", "cómo sobrevivir", "como sobrevivir",
    "cómo rendirme", "como rendirme", "cómo soltarlo", "como soltarlo",
    # Preguntas sobre qué me afecta
    "qué me aporta", "que me aporta", "qué me quita", "que me quita",
    "qué me limita", "que me limita", "qué me pesa", "que me pesa",
    "qué me ancla", "que me ancla", "qué me ciega", "que me ciega",
    "qué elijo", "que elijo", "qué sacrifico", "que sacrifico",
    "qué arriesgo", "que arriesgo", "qué pierdo", "que pierdo",
    "qué gano", "que gano", "qué priorizo", "que priorizo",
    # Segunda oportunidad y reconciliación
    "segunda oportunidad", "volver a intentarlo", "perdonar y olvidar",
    "dar otra oportunidad", "soltar el pasado", "reencuentro",
    "reconciliar", "empezar de cero",
    # Psicología y patrones profundos
    "patrón familiar", "patron familiar", "repetición de patrones", "repeticion de patrones",
    "herida de infancia", "niño interior", "nino interior",
    "herencia emocional", "generacional", "sombra",
    "intuición", "intuicion", "inconsciente",
    # Trabajo interior y espiritualidad profunda
    "yo superior", "yo interior", "propósito del alma", "proposito del alma",
    "fluir con", "rendición", "rendicion", "fe ciega", "confianza ciega",
    "chakras", "tercer ojo", "kundalini",
    "limpieza energética", "limpieza energetica",
    "curación energética", "curacion energetica",
    "meditación", "meditacion", "mindfulness",
    # Salud adicional
    "dolor crónico", "dolor cronico", "enfermedad crónica", "enfermedad cronica",
    "bienestar", "energía vital", "energia vital",
    # Social y colectivo
    "socio", "socios", "sociedad mercantil",
    "compañeros de trabajo", "grupo de amigos", "comunidad",
    # Qué siente/piensa/quiere la otra persona (muy común en tarot)
    "qué siente", "que siente", "qué piensa", "que piensa",
    "qué quiere", "que quiere", "qué busca", "que busca",
    "qué pretende", "que pretende", "qué esconde", "que esconde",
    "qué oculta", "que oculta", "cuáles son sus intenciones", "cuales son sus intenciones",
    "su verdadera intención", "su verdadera intencion",
    "qué hay detrás", "que hay detras", "qué no veo", "que no veo",
    "cuál es la verdad", "cual es la verdad", "la verdad sobre", "la verdad de",
    "qué tengo que aprender", "que tengo que aprender",
    # Más "cómo" de acción
    "cómo demostrar", "como demostrar", "cómo mantener", "como mantener",
    "cómo fortalecer", "como fortalecer", "cómo construir", "como construir",
    "cómo terminar con", "como terminar con", "cómo acabar con", "como acabar con",
    "cómo evitar", "como evitar", "cómo prevenir", "como prevenir",
    "cómo detectar", "como detectar", "cómo reconocer", "como reconocer",
    "cómo descubrir", "como descubrir", "cómo vencer", "como vencer",
    # Esotérico latinoamericano y prácticas mágicas
    "amarre", "endulzamiento", "despojo", "limpia espiritual",
    "me hicieron un trabajo", "trabajo de brujería", "trabajo de brujeria",
    "velón", "velon", "sahumerio",
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
