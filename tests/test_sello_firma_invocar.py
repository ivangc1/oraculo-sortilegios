"""Tests para los 3 nuevos handlers: /sello, /firma, /invocar."""

from bot.handlers.firma import _firma_path
from bot.handlers.invocar import _parse_invocar_args
from bot.handlers.sello import sello_command  # noqa: F401 — smoke import
from bot.handlers.demonio import _load_data as _load_demon_data
from bot.handlers.angel import _load_data as _load_angel_data
from service.prompts.invocar import get_sub_prompt as invocar_sub_prompt


# === /firma ===


def test_firma_path_function():
    """_firma_path devuelve Path o None sin crashear."""
    result = _firma_path(1)
    assert result is None or result.exists()


def test_firma_path_all_angels():
    """_firma_path funciona para los 72 ángeles sin error."""
    for n in range(1, 73):
        result = _firma_path(n)
        assert result is None or result.suffix == ".png"


def test_firma_path_invalid_number():
    """_firma_path con número inválido devuelve None."""
    assert _firma_path(0) is None
    assert _firma_path(73) is None
    assert _firma_path(999) is None


# === /invocar: parseo de args ===


def test_invocar_parse_empty_args():
    """Sin args → entidad aleatoria válida + sin pregunta."""
    entity, etype, q, err = _parse_invocar_args([], user_id=30001)
    assert err is None
    assert entity is not None
    assert etype in ("demonio", "angel")
    assert q is None


def test_invocar_parse_by_name_demon():
    """Nombre de demonio → entity_type=demonio."""
    entity, etype, q, err = _parse_invocar_args(["Bael"], user_id=30002)
    assert err is None
    assert etype == "demonio"
    assert entity["name"] == "Bael"
    assert q is None


def test_invocar_parse_by_name_angel():
    """Nombre de ángel → entity_type=angel."""
    entity, etype, q, err = _parse_invocar_args(["Vehuiah"], user_id=30003)
    assert err is None
    assert etype == "angel"
    assert entity["name"] == "Vehuiah"
    assert q is None


def test_invocar_parse_number_defaults_to_demon():
    """Número sin prefijo → demonio por defecto."""
    entity, etype, q, err = _parse_invocar_args(["1"], user_id=30004)
    assert err is None
    assert etype == "demonio"
    assert entity["number"] == 1


def test_invocar_parse_forced_angel_by_number():
    """'angel 1' → ángel #1 (Vehuiah)."""
    entity, etype, q, err = _parse_invocar_args(["angel", "1"], user_id=30005)
    assert err is None
    assert etype == "angel"
    assert entity["number"] == 1
    assert entity["name"] == "Vehuiah"


def test_invocar_parse_forced_demon_by_number():
    """'demonio 1' → demonio #1 (Bael)."""
    entity, etype, q, err = _parse_invocar_args(["demonio", "1"], user_id=30006)
    assert err is None
    assert etype == "demonio"
    assert entity["number"] == 1
    assert entity["name"] == "Bael"


def test_invocar_parse_with_question():
    """Nombre + pregunta → entity + pregunta no vacía."""
    entity, etype, q, err = _parse_invocar_args(
        ["Bael", "dime", "cómo", "ganar"], user_id=30007,
    )
    assert err is None
    assert entity["name"] == "Bael"
    assert q == "dime cómo ganar"


def test_invocar_parse_forced_type_with_question():
    """'angel Vehuiah ...' → ángel + pregunta."""
    entity, etype, q, err = _parse_invocar_args(
        ["angel", "Vehuiah", "dame", "fuerza"], user_id=30008,
    )
    assert err is None
    assert etype == "angel"
    assert entity["name"] == "Vehuiah"
    assert q == "dame fuerza"


def test_invocar_parse_invalid_demon_name():
    """Forzar demonio con nombre inexistente → error."""
    entity, etype, q, err = _parse_invocar_args(
        ["demonio", "NoExiste"], user_id=30009,
    )
    assert err == "demon_not_found"


def test_invocar_parse_invalid_angel_name():
    """Forzar ángel con nombre inexistente → error."""
    entity, etype, q, err = _parse_invocar_args(
        ["angel", "NoExiste"], user_id=30010,
    )
    assert err == "angel_not_found"


def test_invocar_parse_random_gibberish_becomes_question():
    """Texto que no matchea nada → random demonio + todo como pregunta."""
    entity, etype, q, err = _parse_invocar_args(
        ["xzqkj", "dime", "algo"], user_id=30011,
    )
    assert err is None
    assert entity is not None
    assert q and "xzqkj" in q


# === /invocar: sub-prompt ===


def test_invocar_subprompt_without_entity_is_base():
    """Sin entity → sub-prompt base con instrucciones generales."""
    prompt = invocar_sub_prompt()
    assert "INVOCACIÓN" in prompt
    assert "PRIMERA PERSONA" in prompt


def test_invocar_subprompt_with_demon_includes_canon():
    """Con demonio → sub-prompt incluye nombre, rango y descripción."""
    _load_demon_data()
    from bot.handlers.demonio import _GOETIA
    demon = _GOETIA[0]  # Bael
    prompt = invocar_sub_prompt(demon, "demonio")
    assert demon["name"] in prompt
    assert demon["rank"] in prompt
    assert "Ars Goetia" in prompt


def test_invocar_subprompt_with_angel_includes_canon():
    """Con ángel → sub-prompt incluye coro, virtud y nombre hebreo."""
    _load_angel_data()
    from bot.handlers.angel import _SHEM
    angel = _SHEM[0]  # Vehuiah
    prompt = invocar_sub_prompt(angel, "angel")
    assert angel["name"] in prompt
    assert angel["choir"] in prompt
    assert "Shem HaMephorash" in prompt


def test_invocar_subprompt_demon_vs_angel_differ():
    """Los contextos de demonio y ángel son distintos."""
    _load_demon_data()
    _load_angel_data()
    from bot.handlers.demonio import _GOETIA
    from bot.handlers.angel import _SHEM
    prompt_d = invocar_sub_prompt(_GOETIA[0], "demonio")
    prompt_a = invocar_sub_prompt(_SHEM[0], "angel")
    assert prompt_d != prompt_a
    assert "Infierno" in prompt_d
    assert "Infierno" not in prompt_a


# === /invocar welcome builder (flujo pending sin pregunta) ===


def test_invocar_welcome_demon_contains_name_rank_legions():
    """El welcome de demonio incluye nombre, rango y legiones."""
    _load_demon_data()
    from bot.handlers.demonio import _GOETIA
    from bot.handlers.invocar import _build_invocation_welcome
    bael = _GOETIA[0]  # Bael: Rey, 66 legiones
    welcome = _build_invocation_welcome(bael, "demonio")
    assert "Bael" in welcome
    assert "Rey" in welcome
    assert "66" in welcome
    assert "5 minutos" in welcome


def test_invocar_welcome_angel_contains_name_choir_attribute():
    """El welcome de ángel incluye nombre, coro y atributo."""
    _load_angel_data()
    from bot.handlers.angel import _SHEM
    from bot.handlers.invocar import _build_invocation_welcome
    vehuiah = _SHEM[0]  # Vehuiah: Serafines
    welcome = _build_invocation_welcome(vehuiah, "angel")
    assert "Vehuiah" in welcome
    assert "Serafines" in welcome
    assert "5 minutos" in welcome


def test_invocar_welcome_demon_uses_personality():
    """El welcome incluye la primera frase del personality canónico."""
    _load_demon_data()
    from bot.handlers.demonio import _GOETIA
    from bot.handlers.invocar import _build_invocation_welcome
    bael = _GOETIA[0]
    welcome = _build_invocation_welcome(bael, "demonio")
    # La primera frase de Bael personality: "Voz ronca de autoridad absoluta..."
    assert "Voz ronca" in welcome or "autoridad" in welcome


def test_invocar_welcome_is_distinct_per_entity():
    """El welcome es distinto para dos demonios distintos."""
    _load_demon_data()
    from bot.handlers.demonio import _GOETIA
    from bot.handlers.invocar import _build_invocation_welcome
    w1 = _build_invocation_welcome(_GOETIA[0], "demonio")  # Bael
    w3 = _build_invocation_welcome(_GOETIA[2], "demonio")  # Vassago
    assert w1 != w3
    assert "Bael" in w1 and "Vassago" in w3


def test_invocar_welcome_all_72_demons_build_ok():
    """Construir welcome para los 72 demonios no revienta."""
    _load_demon_data()
    from bot.handlers.demonio import _GOETIA
    from bot.handlers.invocar import _build_invocation_welcome
    for demon in _GOETIA:
        welcome = _build_invocation_welcome(demon, "demonio")
        assert isinstance(welcome, str) and len(welcome) > 50
        assert demon["name"] in welcome


def test_invocar_welcome_all_72_angels_build_ok():
    """Construir welcome para los 72 ángeles no revienta."""
    _load_angel_data()
    from bot.handlers.angel import _SHEM
    from bot.handlers.invocar import _build_invocation_welcome
    for angel in _SHEM:
        welcome = _build_invocation_welcome(angel, "angel")
        assert isinstance(welcome, str) and len(welcome) > 50
        assert angel["name"] in welcome


# === Shem data integridad (personality añadido en v1.197) ===


def test_shem_all_have_personality():
    """Los 72 ángeles Shem tienen el campo personality (no vacío, ≥40 chars)."""
    _load_angel_data()
    from bot.handlers.angel import _SHEM
    for angel in _SHEM:
        personality = angel.get("personality")
        assert isinstance(personality, str), (
            f"Ángel {angel['number']} ({angel['name']}) falta personality"
        )
        assert len(personality) >= 40, (
            f"Ángel {angel['number']} ({angel['name']}) personality demasiado corto: "
            f"'{personality}'"
        )


def test_invocar_subprompt_angel_uses_personality():
    """El sub-prompt de ángel inyecta personality cuando existe."""
    _load_angel_data()
    from bot.handlers.angel import _SHEM
    vehuiah = _SHEM[0]
    prompt = invocar_sub_prompt(vehuiah, "angel")
    # La personality de Vehuiah habla de "ardiente"
    assert "PERSONALIDAD CANÓNICA" in prompt
    assert vehuiah["personality"][:30] in prompt


def test_invocar_subprompt_demon_and_angel_both_have_personality_block():
    """Ambos sub-prompts (demonio y ángel) incluyen el bloque de personalidad."""
    _load_demon_data()
    _load_angel_data()
    from bot.handlers.demonio import _GOETIA
    from bot.handlers.angel import _SHEM
    prompt_d = invocar_sub_prompt(_GOETIA[0], "demonio")
    prompt_a = invocar_sub_prompt(_SHEM[0], "angel")
    assert "PERSONALIDAD CANÓNICA" in prompt_d
    assert "PERSONALIDAD CANÓNICA" in prompt_a
