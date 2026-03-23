"""Configuración centralizada con pydantic-settings. Dev/prod via ENV."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Entorno
    ENV: str = "dev"
    BOT_VERSION: str = "1.0.0"

    # Telegram
    BOT_TOKEN: str
    ALLOWED_CHAT_ID: int
    ALLOWED_THREAD_ID: int | None = None
    ADMIN_USER_ID: int

    # Anthropic
    ANTHROPIC_API_KEY: str
    ANTHROPIC_API_VERSION: str = "2024-10-22"

    # Límites
    MONTHLY_SPENDING_LIMIT: float = 25.0
    DAILY_ALERT_THRESHOLD: float = 5.0
    QUEUE_TIMEOUT: float = 45.0
    FEEDBACK_EXPIRY_DAYS: int = 7

    # Límites de uso diario
    DAILY_DIVINATION_POOL: int = 5
    DAILY_NUMEROLOGIA_LIMIT: int = 2
    DAILY_NATAL_LIMIT: int = 1
    DAILY_ORACULO_LIMIT: int = 3
    COOLDOWN_SECONDS: int = 60
    MAX_QUESTION_LENGTH: int = 200

    # Concurrencia
    MAX_CONCURRENT_API: int = 3

    # max_tokens por modo (configurables sin redeploy)
    MAX_TOKENS_TAROT_1: int = 400
    MAX_TOKENS_TAROT_3: int = 800
    MAX_TOKENS_TAROT_CRUZ: int = 1800
    MAX_TOKENS_RUNAS_1: int = 400
    MAX_TOKENS_RUNAS_3: int = 800
    MAX_TOKENS_RUNAS_CRUZ: int = 1000
    MAX_TOKENS_ICHING: int = 1000
    MAX_TOKENS_GEOMANCIA_1: int = 400
    MAX_TOKENS_GEOMANCIA_ESCUDO: int = 1800
    MAX_TOKENS_NUMEROLOGIA: int = 1000
    MAX_TOKENS_NUMEROLOGIA_COMPAT: int = 700
    MAX_TOKENS_NATAL_TROPICAL: int = 3000
    MAX_TOKENS_NATAL_VEDICA: int = 3000
    MAX_TOKENS_ORACULO: int = 600

    def get_max_tokens(self, mode: str, variant: str) -> int:
        """Devuelve max_tokens para un modo/variante."""
        key_map = {
            ("tarot", "1_carta"): self.MAX_TOKENS_TAROT_1,
            ("tarot", "3_cartas"): self.MAX_TOKENS_TAROT_3,
            ("tarot", "cruz_celta"): self.MAX_TOKENS_TAROT_CRUZ,
            ("runas", "odin"): self.MAX_TOKENS_RUNAS_1,
            ("runas", "nornas"): self.MAX_TOKENS_RUNAS_3,
            ("runas", "cruz"): self.MAX_TOKENS_RUNAS_CRUZ,
            ("iching", "hexagrama"): self.MAX_TOKENS_ICHING,
            ("geomancia", "1_figura"): self.MAX_TOKENS_GEOMANCIA_1,
            ("geomancia", "escudo"): self.MAX_TOKENS_GEOMANCIA_ESCUDO,
            ("numerologia", "informe"): self.MAX_TOKENS_NUMEROLOGIA,
            ("numerologia", "compatibilidad"): self.MAX_TOKENS_NUMEROLOGIA_COMPAT,
            ("natal", "tropical"): self.MAX_TOKENS_NATAL_TROPICAL,
            ("natal", "vedica"): self.MAX_TOKENS_NATAL_VEDICA,
            ("oraculo", "libre"): self.MAX_TOKENS_ORACULO,
        }
        return key_map.get((mode, variant), 600)


def load_settings() -> Settings:
    """Carga settings desde .env. Falla rápido si faltan variables obligatorias."""
    return Settings()
