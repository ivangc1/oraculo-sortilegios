"""Tests del selector inteligente de tirada."""

import pytest

from service.smart_selector import select_variant, variant_label


class TestYesNo:
    """Preguntas si/no → 1_carta."""

    @pytest.mark.parametrize("q", [
        "¿Debería cambiar de trabajo?",
        "deberia dejar a mi pareja",
        "¿Puedo confiar en esa persona?",
        "¿Va a funcionar este negocio?",
        "¿Me conviene mudarme?",
        "¿Voy a aprobar el examen?",
        "¿Es bueno aceptar esa oferta?",
        "¿Será que me quiere de verdad?",
        "¿Habrá cambios en mi vida?",
        "¿Me quiere?",
        "¿Le gusto a esa persona?",
        "¿Volverá a buscarme?",
        "¿Funcionará mi proyecto?",
        "¿Merece la pena seguir?",
        "pregunta sí o no",
        "si o no",
        "¿Es verdad que me engaña?",
        "¿Tengo que irme ya?",
        "¿Puede ser que mienta?",
    ])
    def test_yes_no_questions(self, q):
        assert select_variant(q) == "1_carta"


class TestTemporal:
    """Preguntas temporales → 3_cartas."""

    @pytest.mark.parametrize("q", [
        "¿Cómo va a evolucionar mi relación?",
        "¿Qué me espera en el futuro?",
        "¿Qué pasó con aquella oportunidad?",
        "¿Hacia dónde va mi carrera?",
        "¿Cuál es la tendencia de mi situación?",
        "¿Qué viene después de esto?",
        "Quiero saber sobre mi camino",
        "¿Cómo va mi situación laboral?",
        "progreso en mi vida sentimental",
    ])
    def test_temporal_questions(self, q):
        assert select_variant(q) == "3_cartas"


class TestComplex:
    """Preguntas complejas → cruz_celta."""

    @pytest.mark.parametrize("q", [
        "¿Qué está pasando en mi relación con mi madre?",
        "¿Por qué no avanzo en la vida?",
        "Tengo un conflicto con mi jefe y no sé qué hacer",
        "Estoy estancada y necesito entender qué me bloquea",
        "¿Qué pasa con mi situación económica?",
        "No consigo avanzar en nada",
        "Es un dilema muy complicado",
    ])
    def test_complex_questions(self, q):
        assert select_variant(q) == "cruz_celta"

    def test_long_question_is_complex(self):
        long_q = " ".join(["palabra"] * 35)
        assert select_variant(long_q) == "cruz_celta"


class TestDefault:
    """Preguntas ambiguas → 3_cartas (default)."""

    @pytest.mark.parametrize("q", [
        "amor",
        "trabajo",
        "dime algo sobre mi vida",
        "¿Qué me dicen las cartas?",
    ])
    def test_default_questions(self, q):
        assert select_variant(q) == "3_cartas"

    def test_orientacion_es_complejo(self):
        """Pedir orientación merece Cruz Celta, no default."""
        assert select_variant("necesito orientación") == "cruz_celta"


class TestEdgeCases:
    def test_empty_string(self):
        assert select_variant("") == "3_cartas"

    def test_none_like(self):
        assert select_variant("   ") == "3_cartas"

    def test_single_word(self):
        assert select_variant("hola") == "3_cartas"

    def test_accents_preserved(self):
        assert select_variant("¿debería irme?") == "1_carta"
        assert select_variant("¿deberia irme?") == "1_carta"


class TestPriorityOrder:
    """Verifica que la prioridad si_no > temporal > complejo se respeta."""

    def test_yes_no_wins_over_temporal(self):
        """Si/no al inicio gana sobre keywords temporales."""
        assert select_variant("¿debería esperar al futuro?") == "1_carta"

    def test_yes_no_wins_over_complex(self):
        """Si/no al inicio gana sobre keywords complejos."""
        assert select_variant("¿debería dejar la relación?") == "1_carta"

    def test_temporal_wins_over_complex(self):
        """Keyword temporal gana sobre keyword complejo."""
        assert select_variant("¿cómo evolucionará mi relación?") == "3_cartas"

    def test_long_question_wins_over_all(self):
        """Pregunta >30 palabras siempre va a cruz_celta."""
        q = " ".join(["palabra"] * 31)
        assert select_variant(q) == "cruz_celta"


class TestVariantLabel:
    def test_known_labels(self):
        assert "carta" in variant_label("1_carta").lower()
        assert "Cruz Celta" in variant_label("cruz_celta")
        assert "Herradura" in variant_label("herradura")

    def test_unknown_returns_key(self):
        assert variant_label("inventado") == "inventado"
