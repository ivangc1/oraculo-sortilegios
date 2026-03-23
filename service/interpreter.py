"""Servicio de interpretación: orquesta sub-prompts + Anthropic client."""

from service.anthropic_client import AnthropicService
from service.models import InterpretationRequest, InterpretationResponse


class InterpreterService:
    """Capa 2: recibe InterpretationRequest, construye user message, llama a Anthropic."""

    def __init__(self, anthropic_service: AnthropicService):
        self._anthropic = anthropic_service

    async def interpret(self, request: InterpretationRequest) -> InterpretationResponse:
        """Genera interpretación completa."""
        user_message = self._build_user_message(request)
        return await self._anthropic.interpret(request, user_message)

    def _build_user_message(self, request: InterpretationRequest) -> str:
        """Construye el user message con sub-prompt + datos + perfil + pregunta."""
        parts = []

        # Sub-prompt del modo
        sub_prompt = self._get_sub_prompt(request.mode, request.variant)
        if sub_prompt:
            parts.append(f"<instrucciones_modo>\n{sub_prompt}\n</instrucciones_modo>")

        # Perfil del usuario
        profile_fragment = request.user_profile.to_prompt_fragment()
        parts.append(f"<perfil_consultante>\n{profile_fragment}\n</perfil_consultante>")

        # Datos de la tirada
        if request.drawn_items:
            items_text = self._format_drawn_items(request)
            parts.append(f"<tirada>\n{items_text}\n</tirada>")

        # Datos extra (hexagramas, escudo, natal, etc.)
        if request.extra_data:
            extra_text = self._format_extra_data(request.extra_data)
            parts.append(f"<datos_extra>\n{extra_text}\n</datos_extra>")

        # Pregunta
        if request.question:
            parts.append(f"<pregunta>\n{request.question}\n</pregunta>")
        else:
            parts.append("<sin_pregunta>Lectura general, sin pregunta específica.</sin_pregunta>")

        return "\n\n".join(parts)

    def _get_sub_prompt(self, mode: str, variant: str) -> str | None:
        """Carga sub-prompt según modo/variante. Importaciones lazy."""
        try:
            if mode == "tarot":
                from service.prompts.tarot import get_sub_prompt
                return get_sub_prompt(variant)
            elif mode == "runas":
                from service.prompts.runas import get_sub_prompt
                return get_sub_prompt(variant)
            elif mode == "iching":
                from service.prompts.iching import get_sub_prompt
                return get_sub_prompt(variant)
            elif mode == "geomancia":
                from service.prompts.geomancia import get_sub_prompt
                return get_sub_prompt(variant)
            elif mode == "numerologia":
                from service.prompts.numerologia import get_sub_prompt
                return get_sub_prompt(variant)
            elif mode == "natal":
                if variant == "tropical":
                    from service.prompts.natal_tropical import get_sub_prompt
                    return get_sub_prompt()
                elif variant == "vedica":
                    from service.prompts.natal_vedica import get_sub_prompt
                    return get_sub_prompt()
            elif mode == "oraculo":
                from service.prompts.oraculo import get_sub_prompt
                return get_sub_prompt()
        except ImportError:
            pass
        return None

    def _format_drawn_items(self, request: InterpretationRequest) -> str:
        lines = []
        for item in request.drawn_items:
            parts = [f"{item.name}"]
            if item.inverted:
                parts.append("(invertida)")
            if item.position:
                parts.append(f"— posición: {item.position}")
            lines.append(" ".join(parts))
        return "\n".join(lines)

    def _format_extra_data(self, extra: dict) -> str:
        lines = []
        for key, value in extra.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)
