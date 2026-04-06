"""Modelos Pydantic para comunicación entre capas Bot y Servicio."""

from pydantic import BaseModel, field_validator


class UserProfile(BaseModel):
    """Perfil del usuario inyectado en cada interpretación (~15-40 tokens)."""
    alias: str
    sun_sign: str | None = None
    moon_sign: str | None = None
    ascendant: str | None = None
    lunar_nakshatra: str | None = None
    life_path: int | None = None

    def to_prompt_fragment(self) -> str:
        """Genera fragmento de perfil para inyectar en user message."""
        parts = [f"Alias: {self.alias}"]
        if self.sun_sign:
            parts.append(f"Sol: {self.sun_sign}")
        if self.moon_sign:
            parts.append(f"Luna: {self.moon_sign}")
        if self.ascendant:
            parts.append(f"Ascendente: {self.ascendant}")
        if self.lunar_nakshatra:
            parts.append(f"Nakshatra lunar: {self.lunar_nakshatra}")
        if self.life_path is not None:
            parts.append(f"Camino de vida: {self.life_path}")
        return " | ".join(parts)


    @classmethod
    def from_db_or_guest(cls, user: dict | None, update) -> "UserProfile":
        """Perfil desde DB o guest con nombre de Telegram."""
        if user and user.get("onboarding_complete"):
            return cls(
                alias=user["alias"],
                sun_sign=user.get("sun_sign"),
                moon_sign=user.get("moon_sign"),
                ascendant=user.get("ascendant"),
                lunar_nakshatra=user.get("lunar_nakshatra"),
                life_path=user.get("life_path"),
            )
        # Guest: usar first_name de Telegram
        name = "Consultante"
        if update and update.effective_user:
            name = update.effective_user.first_name or "Consultante"
        return cls(alias=name)


class DrawnItem(BaseModel):
    """Un elemento tirado (carta, runa, figura, etc.)."""
    id: str
    name: str
    inverted: bool = False
    position: str | None = None
    extra: dict | None = None


class InterpretationRequest(BaseModel):
    """Petición de interpretación: Capa Bot → Capa Servicio."""
    mode: str
    variant: str
    deck: str | None = None  # mazo de tarot (rws, marsella)
    drawn_items: list[DrawnItem] = []
    question: str | None = None
    user_profile: UserProfile
    max_tokens: int = 600
    effort: str = "medium"  # adaptive thinking: low/medium/high
    extra_data: dict | None = None

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 500:
            v = v[:500]
        return v

    @classmethod
    def build(cls, **data) -> "InterpretationRequest":
        return cls.model_validate(data)


class InterpretationResponse(BaseModel):
    """Respuesta de interpretación: Capa Servicio → Capa Bot."""
    text: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    cached: bool = False
    truncated: bool = False
    error: str | None = None
