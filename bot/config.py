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
    ANTHROPIC_API_VERSION: str = "2023-06-01"

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

    # UX
    USE_BLOCKQUOTE: bool = True  # Blockquote expandible en lecturas largas (por variante)

    # Concurrencia
    MAX_CONCURRENT_API: int = 3

    # Thinking effort por modo (adaptive thinking Sonnet 4.6: low/medium/high)
    EFFORT_TAROT_1: str = "low"
    EFFORT_TAROT_3: str = "medium"
    EFFORT_TAROT_CRUZ: str = "high"
    EFFORT_RUNAS_1: str = "low"
    EFFORT_RUNAS_3: str = "medium"
    EFFORT_RUNAS_CRUZ: str = "high"
    EFFORT_ICHING: str = "high"
    EFFORT_GEOMANCIA_1: str = "low"
    EFFORT_GEOMANCIA_ESCUDO: str = "high"
    EFFORT_NUMEROLOGIA: str = "medium"
    EFFORT_NUMEROLOGIA_COMPAT: str = "medium"
    EFFORT_NATAL_TROPICAL: str = "high"
    EFFORT_NATAL_VEDICA: str = "high"
    EFFORT_TAROT_HERRADURA: str = "high"
    EFFORT_TAROT_RELACION: str = "high"
    EFFORT_TAROT_ESTRELLA: str = "high"
    EFFORT_TAROT_CRUZ_SIMPLE: str = "medium"
    EFFORT_TAROT_SINO: str = "medium"
    EFFORT_TAROT_DIA: str = "low"
    EFFORT_RUNAS_CINCO: str = "high"
    EFFORT_RUNAS_SIETE: str = "high"
    EFFORT_ORACULO: str = "medium"

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
    MAX_TOKENS_TAROT_HERRADURA: int = 1500
    MAX_TOKENS_TAROT_RELACION: int = 1200
    MAX_TOKENS_TAROT_ESTRELLA: int = 1200
    MAX_TOKENS_TAROT_CRUZ_SIMPLE: int = 1000
    MAX_TOKENS_TAROT_SINO: int = 600
    MAX_TOKENS_TAROT_DIA: int = 400
    MAX_TOKENS_RUNAS_CINCO: int = 1000
    MAX_TOKENS_RUNAS_SIETE: int = 1500
    MAX_TOKENS_ORACULO: int = 600

    def get_max_tokens(self, mode: str, variant: str) -> int:
        """Devuelve max_tokens para un modo/variante."""
        key_map = {
            ("tarot", "1_carta"): self.MAX_TOKENS_TAROT_1,
            ("tarot", "3_cartas"): self.MAX_TOKENS_TAROT_3,
            ("tarot", "cruz_celta"): self.MAX_TOKENS_TAROT_CRUZ,
            ("tarot", "herradura"): self.MAX_TOKENS_TAROT_HERRADURA,
            ("tarot", "relacion"): self.MAX_TOKENS_TAROT_RELACION,
            ("tarot", "estrella"): self.MAX_TOKENS_TAROT_ESTRELLA,
            ("tarot", "cruz_simple"): self.MAX_TOKENS_TAROT_CRUZ_SIMPLE,
            ("tarot", "si_no"): self.MAX_TOKENS_TAROT_SINO,
            ("tarot", "tirada_dia"): self.MAX_TOKENS_TAROT_DIA,
            ("runas", "odin"): self.MAX_TOKENS_RUNAS_1,
            ("runas", "nornas"): self.MAX_TOKENS_RUNAS_3,
            ("runas", "cruz"): self.MAX_TOKENS_RUNAS_CRUZ,
            ("runas", "cinco"): self.MAX_TOKENS_RUNAS_CINCO,
            ("runas", "siete"): self.MAX_TOKENS_RUNAS_SIETE,
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

    def get_effort(self, mode: str, variant: str) -> str:
        """Devuelve thinking effort para un modo/variante (low/medium/high)."""
        key_map = {
            ("tarot", "1_carta"): self.EFFORT_TAROT_1,
            ("tarot", "3_cartas"): self.EFFORT_TAROT_3,
            ("tarot", "cruz_celta"): self.EFFORT_TAROT_CRUZ,
            ("tarot", "herradura"): self.EFFORT_TAROT_HERRADURA,
            ("tarot", "relacion"): self.EFFORT_TAROT_RELACION,
            ("tarot", "estrella"): self.EFFORT_TAROT_ESTRELLA,
            ("tarot", "cruz_simple"): self.EFFORT_TAROT_CRUZ_SIMPLE,
            ("tarot", "si_no"): self.EFFORT_TAROT_SINO,
            ("tarot", "tirada_dia"): self.EFFORT_TAROT_DIA,
            ("runas", "odin"): self.EFFORT_RUNAS_1,
            ("runas", "nornas"): self.EFFORT_RUNAS_3,
            ("runas", "cruz"): self.EFFORT_RUNAS_CRUZ,
            ("runas", "cinco"): self.EFFORT_RUNAS_CINCO,
            ("runas", "siete"): self.EFFORT_RUNAS_SIETE,
            ("iching", "hexagrama"): self.EFFORT_ICHING,
            ("geomancia", "1_figura"): self.EFFORT_GEOMANCIA_1,
            ("geomancia", "escudo"): self.EFFORT_GEOMANCIA_ESCUDO,
            ("numerologia", "informe"): self.EFFORT_NUMEROLOGIA,
            ("numerologia", "compatibilidad"): self.EFFORT_NUMEROLOGIA_COMPAT,
            ("natal", "tropical"): self.EFFORT_NATAL_TROPICAL,
            ("natal", "vedica"): self.EFFORT_NATAL_VEDICA,
            ("oraculo", "libre"): self.EFFORT_ORACULO,
        }
        return key_map.get((mode, variant), "medium")

    # Variantes que usan blockquote expandible (lecturas largas)
    _BLOCKQUOTE_VARIANTS = frozenset({
        ("tarot", "1_carta"),
        ("tarot", "3_cartas"),
        ("tarot", "cruz_celta"),
        ("tarot", "cruz_simple"),
        ("tarot", "herradura"),
        ("tarot", "estrella"),
        ("tarot", "relacion"),
        ("tarot", "si_no"),
        ("tarot", "tirada_dia"),
        ("natal", "tropical"),
        ("natal", "vedica"),
        ("runas", "siete"),
        ("geomancia", "escudo"),
        ("iching", "hexagrama"),
    })

    def use_blockquote_for(self, mode: str, variant: str) -> bool:
        """True si esta variante debe usar blockquote expandible."""
        if not self.USE_BLOCKQUOTE:
            return False
        return (mode, variant) in self._BLOCKQUOTE_VARIANTS


def load_settings() -> Settings:
    """Carga settings desde .env. Falla rápido si faltan variables obligatorias."""
    return Settings()
