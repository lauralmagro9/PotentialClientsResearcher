"""Integration tests for services.gemini_service against the Gemini API."""

from researcher.services.gemini_service import classification_agent


class Test0ClassificationAgent:
    """Tests for classification_agent against the live Gemini API."""

    def test_0_classification_agent_assigns_tier_and_reason(self):
        """Verify that Gemini classifies a known restaurant and records a reason."""
        places = [
            {
                "Nombre": "El Celler de Can Roca",
                "Web": "https://cellercanroca.com",
                "Precio (nivel Google)": "PRICE_LEVEL_VERY_EXPENSIVE",
            }
        ]

        result = classification_agent(places)

        assert len(result) == 1
        assert result[0]["Nombre"] == "El Celler de Can Roca"
        assert result[0]["Tier"] in {"Tier 1", "Tier 2", "Tier 3"}
        assert result[0]["Motivo agente"]
        assert result[0]["Tier"] != "Error"
