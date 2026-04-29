"""Tests de modelos Pydantic."""

import pytest
from pydantic import ValidationError

from service.models import (
    DrawnItem,
    InterpretationRequest,
    InterpretationResponse,
    UserProfile,
)


def test_user_profile_minimal():
    profile = UserProfile(alias="TestUser")
    assert profile.alias == "TestUser"
    assert profile.sun_sign is None


def test_user_profile_to_prompt():
    profile = UserProfile(
        alias="Luna", sun_sign="Escorpio", life_path=7
    )
    fragment = profile.to_prompt_fragment()
    assert "Luna" in fragment
    assert "Escorpio" in fragment
    assert "7" in fragment


def test_interpretation_request_build():
    req = InterpretationRequest.build(
        mode="tarot",
        variant="1_carta",
        drawn_items=[{"id": "major_00", "name": "El Loco", "inverted": True}],
        user_profile={"alias": "Test"},
        max_tokens=400,
    )
    assert req.mode == "tarot"
    assert req.drawn_items[0].inverted is True


def test_interpretation_request_question_not_truncated():
    """El bot ya no trunca preguntas; pasan íntegras al modelo."""
    long_question = "A" * 600
    req = InterpretationRequest(
        mode="tarot",
        variant="1_carta",
        question=long_question,
        user_profile=UserProfile(alias="Test"),
    )
    assert req.question == long_question


def test_interpretation_request_question_strip():
    req = InterpretationRequest(
        mode="tarot",
        variant="1_carta",
        question="  hola  ",
        user_profile=UserProfile(alias="Test"),
    )
    assert req.question == "hola"


def test_interpretation_response_defaults():
    resp = InterpretationResponse(error="timeout")
    assert resp.text == ""
    assert resp.tokens_input == 0
    assert resp.error == "timeout"
