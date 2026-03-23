"""Tests de admins: grid, bio, búsqueda, mención por user_id."""

import json
from pathlib import Path

import pytest

from bot.handlers.admins import (
    _build_bio_text,
    _build_grid_keyboard,
    _find_admin,
    _load_admins,
    _ADMINS_DATA,
)


@pytest.fixture(autouse=True)
def setup_test_admins(tmp_path, monkeypatch):
    """Crea admins_private.json temporal para tests."""
    import bot.handlers.admins as admins_module

    test_data = [
        {
            "key": "tam",
            "telegram_user_id": 915056450,
            "display_name": "Tam ☥∆Ωπ",
            "username": "Tam170717",
            "bio": "Iniciada practicante en Magia Hermética."
        },
        {
            "key": "void",
            "telegram_user_id": 123456789,
            "display_name": "Void",
            "username": "void_user",
            "bio": "Guardián del vacío."
        },
        {
            "key": "wolf",
            "telegram_user_id": 0,
            "display_name": "Wolf",
            "username": "wolf_user",
            "bio": "Lobo solitario."
        },
    ]

    # Reset module state
    admins_module._ADMINS_DATA = None
    admins_module._ADMINS_BY_KEY = None

    # Write temp file
    admins_path = tmp_path / "admins_private.json"
    admins_path.write_text(json.dumps(test_data, ensure_ascii=False), encoding="utf-8")

    # Monkeypatch the path
    original_load = admins_module._load_admins

    def patched_load():
        admins_module._ADMINS_DATA = test_data
        admins_module._ADMINS_BY_KEY = {a["key"]: a for a in test_data}

    monkeypatch.setattr(admins_module, "_load_admins", patched_load)
    patched_load()

    yield

    admins_module._ADMINS_DATA = None
    admins_module._ADMINS_BY_KEY = None


def test_find_admin_by_key():
    admin = _find_admin("tam")
    assert admin is not None
    assert admin["display_name"] == "Tam ☥∆Ωπ"


def test_find_admin_by_key_case_insensitive():
    admin = _find_admin("TAM")
    assert admin is not None


def test_find_admin_by_username():
    admin = _find_admin("void_user")
    assert admin is not None
    assert admin["key"] == "void"


def test_find_admin_not_found():
    admin = _find_admin("inexistente")
    assert admin is None


def test_bio_with_user_id():
    """Bio con user_id genera mención HTML tg://user."""
    admin = {"display_name": "Void", "telegram_user_id": 123456789, "bio": "Test bio"}
    text = _build_bio_text(admin)
    assert 'tg://user?id=123456789' in text
    assert "Void" in text
    assert "Test bio" in text


def test_bio_without_user_id():
    """Bio sin user_id usa @username."""
    admin = {"display_name": "Wolf", "telegram_user_id": 0,
             "username": "wolf_user", "bio": "Lobo"}
    text = _build_bio_text(admin)
    assert "@wolf_user" in text
    assert "tg://user" not in text


def test_grid_keyboard_structure():
    """Grid tiene filas de 2 botones."""
    kb = _build_grid_keyboard()
    assert kb is not None
    # 3 admins → 2 filas (2+1)
    rows = kb.inline_keyboard
    assert len(rows) == 2
    assert len(rows[0]) == 2
    assert len(rows[1]) == 1


def test_grid_callback_data():
    """Callback data usa formato a:N."""
    kb = _build_grid_keyboard()
    first_btn = kb.inline_keyboard[0][0]
    assert first_btn.callback_data == "a:0"
