"""Tests para los handlers /sello y /firma (assets puros, sin LLM)."""

from bot.handlers.firma import _firma_path


def test_sello_module_imports():
    """Smoke: el módulo /sello carga sin errores (importa demonio + assets)."""
    from bot.handlers.sello import sello_command
    assert sello_command is not None


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
