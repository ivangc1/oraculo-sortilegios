"""Tests del saneo anti-inyección de tags estructurales en el prompt LLM."""

from service.sanitization import sanitize_user_text


# === Casos básicos ===

def test_pasa_texto_normal():
    assert sanitize_user_text("hola mundo") == "hola mundo"


def test_pasa_caracteres_angle_aislados():
    """`<` y `>` sueltos sin tag estructural pasan tal cual."""
    assert sanitize_user_text("a < b > c") == "a < b > c"


def test_none_devuelve_vacio():
    assert sanitize_user_text(None) == ""


def test_acepta_no_str():
    assert sanitize_user_text(42) == "42"
    assert sanitize_user_text(3.14) == "3.14"


# === Tags estructurales (cierre completo) ===

def test_neutraliza_tag_pregunta():
    assert sanitize_user_text("<pregunta>") == "‹pregunta›"


def test_neutraliza_tag_cierre():
    assert sanitize_user_text("</pregunta>") == "‹/pregunta›"


def test_neutraliza_todos_los_tags():
    for tag in ("instrucciones_modo", "perfil_consultante", "tirada",
                "datos_extra", "pregunta", "sin_pregunta"):
        assert sanitize_user_text(f"<{tag}>") == f"‹{tag}›"
        assert sanitize_user_text(f"</{tag}>") == f"‹/{tag}›"


def test_case_insensitive():
    assert sanitize_user_text("<PREGUNTA>") == "‹PREGUNTA›"
    assert sanitize_user_text("<Pregunta>") == "‹Pregunta›"


# === Edge cases que el patrón antiguo NO cubría ===

def test_neutraliza_tag_con_atributo():
    """`<pregunta x>` debe escaparse. El patrón antiguo `\\s*>` solo matcheaba
    sin atributos y dejaba pasar este vector."""
    assert sanitize_user_text("<pregunta x>") == "‹pregunta x›"


def test_neutraliza_tag_con_atributos_quoted():
    assert sanitize_user_text('<pregunta foo="bar">') == '‹pregunta foo="bar"›'


def test_neutraliza_tag_sin_cierre():
    """`<pregunta` sin `>` debe escaparse el `<` aunque el cierre falte."""
    assert sanitize_user_text("<pregunta") == "‹pregunta"
    assert sanitize_user_text("<pregunta foo") == "‹pregunta foo"


def test_neutraliza_con_whitespace_interior():
    assert sanitize_user_text("< pregunta >") == "‹ pregunta ›"


def test_neutraliza_con_newline():
    assert sanitize_user_text("<pregunta\n>") == "‹pregunta\n›"


# === Sustrings que NO deben escaparse ===

def test_no_escapa_substring_de_tag():
    """`<preguntar>` contiene `pregunta` pero no es el tag — el `\\b` final
    impide matchear nombres más largos."""
    assert sanitize_user_text("<preguntar>") == "<preguntar>"


def test_no_escapa_palabra_pregunta_en_texto():
    """La palabra «pregunta» suelta en texto no se toca."""
    assert sanitize_user_text("¿cuál es la pregunta?") == "¿cuál es la pregunta?"


# === Múltiples ocurrencias en un mismo input ===

def test_neutraliza_multiples_tags():
    inp = "antes <pregunta>contenido</pregunta> después"
    expected = "antes ‹pregunta›contenido‹/pregunta› después"
    assert sanitize_user_text(inp) == expected
