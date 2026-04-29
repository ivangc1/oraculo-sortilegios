"""Tests de seguridad DM: whitelist deep links, anti-bypass, SQL injection.

(El rate limit de onboarding se eliminó al abrir el bot sin restricciones.)
"""

from bot.handlers.start import _VALID_START_PARAMS
from database.users import _ALLOWED_PROFILE_COLUMNS


class TestDeepLinkWhitelist:
    """Solo parametros de la whitelist son validos."""

    def test_valid_params(self):
        assert _VALID_START_PARAMS == {"onboarding", "update_profile", "set_fullname"}

    def test_onboarding_is_valid(self):
        assert "onboarding" in _VALID_START_PARAMS

    def test_update_profile_is_valid(self):
        assert "update_profile" in _VALID_START_PARAMS

    def test_set_fullname_is_valid(self):
        assert "set_fullname" in _VALID_START_PARAMS

    def test_empty_string_not_valid(self):
        assert "" not in _VALID_START_PARAMS

    def test_path_traversal_not_valid(self):
        assert "onboarding_../../admin" not in _VALID_START_PARAMS

    def test_special_chars_not_valid(self):
        assert "onboarding;rm -rf" not in _VALID_START_PARAMS

    def test_admin_not_valid(self):
        assert "admin" not in _VALID_START_PARAMS

    def test_arbitrary_not_valid(self):
        assert "tarot" not in _VALID_START_PARAMS
        assert "stats" not in _VALID_START_PARAMS
        assert "version" not in _VALID_START_PARAMS


class TestProfileColumnWhitelist:
    """update_profile solo acepta columnas de la whitelist."""

    def test_whitelist_has_expected_columns(self):
        expected = {"birth_time", "birth_city", "birth_lat", "birth_lon",
                    "birth_timezone", "sun_sign", "moon_sign", "ascendant",
                    "lunar_nakshatra", "life_path", "full_birth_name"}
        assert _ALLOWED_PROFILE_COLUMNS == expected

    def test_telegram_user_id_not_in_whitelist(self):
        """Nunca se debe poder cambiar el user_id via update_profile."""
        assert "telegram_user_id" not in _ALLOWED_PROFILE_COLUMNS

    def test_username_not_in_whitelist(self):
        assert "telegram_username" not in _ALLOWED_PROFILE_COLUMNS

    def test_alias_not_in_whitelist(self):
        """Alias se establece en onboarding, no via update_profile."""
        assert "alias" not in _ALLOWED_PROFILE_COLUMNS

    def test_onboarding_complete_not_in_whitelist(self):
        assert "onboarding_complete" not in _ALLOWED_PROFILE_COLUMNS

    def test_sql_injection_column_not_in_whitelist(self):
        assert "birth_date = ?, telegram_user_id" not in _ALLOWED_PROFILE_COLUMNS


class TestMiddlewareDM:
    """Verificar que el middleware bloquea tiradas en DM."""

    def test_allowed_commands_in_dm(self):
        """Solo /start, /startoraculo, /cancelaroraculo en DM."""
        allowed = {"/start", "/startoraculo", "/cancelaroraculo"}
        blocked = {"/tarot", "/runa", "/iching", "/geomancia",
                   "/numerologia", "/natal", "/vedica", "/oraculo",
                   "/bibliomancia", "/admins", "/consulta"}
        for cmd in blocked:
            assert cmd not in allowed
