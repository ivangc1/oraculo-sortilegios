"""Tests de validación: fechas, preguntas, sanitización."""

from service.models import InterpretationRequest, UserProfile


def test_question_truncated_at_200():
    req = InterpretationRequest(
        mode="oraculo", variant="libre",
        question="X" * 300,
        user_profile=UserProfile(alias="Test"),
    )
    assert len(req.question) == 200


def test_question_stripped():
    req = InterpretationRequest(
        mode="oraculo", variant="libre",
        question="  hola mundo  ",
        user_profile=UserProfile(alias="Test"),
    )
    assert req.question == "hola mundo"


def test_question_none_allowed():
    req = InterpretationRequest(
        mode="tarot", variant="1_carta",
        question=None,
        user_profile=UserProfile(alias="Test"),
    )
    assert req.question is None


def test_empty_question_preserved():
    """Cadena vacía después de strip se mantiene como vacía."""
    req = InterpretationRequest(
        mode="oraculo", variant="libre",
        question="   ",
        user_profile=UserProfile(alias="Test"),
    )
    assert req.question == ""


def test_user_profile_prompt_fragment_minimal():
    profile = UserProfile(alias="Luna")
    fragment = profile.to_prompt_fragment()
    assert "Luna" in fragment
    assert "|" not in fragment  # Solo alias, sin separador


def test_user_profile_prompt_fragment_full():
    profile = UserProfile(
        alias="Luna", sun_sign="Escorpio", moon_sign="Piscis",
        ascendant="Virgo", life_path=7,
    )
    fragment = profile.to_prompt_fragment()
    assert "Luna" in fragment
    assert "Escorpio" in fragment
    assert "Piscis" in fragment
    assert "Virgo" in fragment
    assert "7" in fragment
    assert "|" in fragment  # Múltiples campos separados


def test_control_chars_in_question():
    """Caracteres de control no rompen el modelo."""
    req = InterpretationRequest(
        mode="oraculo", variant="libre",
        question="hola\x00mundo\x01test",
        user_profile=UserProfile(alias="Test"),
    )
    assert req.question is not None
