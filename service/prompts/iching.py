"""Sub-prompts de I Ching (marco Wilhelm)."""


def get_sub_prompt(variant: str) -> str:
    return _SUB_HEXAGRAMA


_SUB_HEXAGRAMA = """MODO: I Ching — Hexagrama.
Consulta al I Ching según el marco de Richard Wilhelm.

Si hay LÍNEAS MUTABLES (yang viejo = 9, yin viejo = 6):
- Interpreta el hexagrama primario con su juicio e imagen.
- Interpreta las líneas mutables específicas: son el corazón de la consulta.
- Interpreta la transformación al hexagrama derivado: qué cambia y hacia dónde.
- La relación primario → derivado muestra la evolución de la situación.

Si NO hay líneas mutables (todas yang joven = 7 o yin joven = 8):
- Interpreta SOLO el hexagrama primario.
- NO inventes un hexagrama derivado.
- Indica que la situación es estable, sin transformación en curso.
- La ausencia de mutables es en sí un mensaje: estabilidad, no hay tensión de cambio."""
