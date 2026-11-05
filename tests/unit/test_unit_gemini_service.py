"""Unit tests for services/gemini_service.py.

Tests cover:
- visit_place_url: URL validation, HTTP 200 text extraction, HTML stripping,
  truncation to 3000 chars, non-200 status codes, and network exceptions.
- classification_agent: Gemini chat agent integration, prompt formatting,
  clean JSON responses, markdown code block stripping, API exceptions,
  invalid JSON handling, rate-limit sleep enforcement, and dictionary annotations.
"""

import json
from unittest.mock import MagicMock, patch
from researcher.services.gemini_service import classification_agent, visit_place_url

import httpx
import pandas as pd

# Configure mock settings required by services.gemini_service at import time
mock_settings_dict = {
    "gemini": {
        "API_KEY": "fake-test-key",
        "MODEL": "gemini-test-model",
        "PROMPT_TEMPLATE": "Classify {0} (Web: {1}, price: {2})",
    }
}



# =====================================================================
# Tests for visit_place_url
# =====================================================================
class Test0VisitPlaceUrl:
    """Test suite for the visit_place_url function."""

    @patch("researcher.services.gemini_service.httpx.get")
    def test_0_visit_place_url_empty_or_none_returns_invalid_message(self, mock_get):
        """Test that empty string or None URLs return the invalid URL message without making HTTP requests."""
        for url in ["", None]:
            result = visit_place_url(url)
            assert result == "No hay URL válida disponible."
        mock_get.assert_not_called()

    @patch("researcher.services.gemini_service.httpx.get")
    def test_1_visit_place_url_missing_http_prefix_returns_invalid_message(self, mock_get):
        """Test that URLs without an http:// or https:// prefix return the invalid URL message without making HTTP requests."""
        invalid_urls = [
            "www.lacasona.com",
            "ftp://lacasona.com",
            "lacasona.com",
            "mailto:info@lacasona.com",
            "javascript:void(0)",
        ]
        for url in invalid_urls:
            result = visit_place_url(url)
            assert result == "No hay URL válida disponible."
        mock_get.assert_not_called()

    @patch("researcher.services.gemini_service.httpx.get")
    def test_2_visit_place_url_successful_200_extracts_and_strips_html(self, mock_get, mock_html_content):
        """Test that an HTTP 200 response strips script, style, nav, and footer tags and extracts clean text."""
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html_content
        mock_get.return_value = mock_response

        url = "https://www.asadorelroble.com"
        result = visit_place_url(url)

        mock_get.assert_called_once_with(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8.0,
            follow_redirects=True,
        )
        assert "Asador El Roble" in result
        assert "Especialidad en carnes maduradas y setas silvestres de temporada." in result
        # Check that stripped elements are absent
        assert "Inicio" not in result
        assert "Nuestra Carta" not in result
        assert "analytics initialized" not in result
        assert "font-family" not in result
        assert "secret_12345" not in result
        assert "Todos los derechos reservados" not in result

    @patch("researcher.services.gemini_service.httpx.get")
    def test_3_visit_place_url_truncates_text_to_3000_chars(self, mock_get):
        """Test that extracted visible text exceeding 3000 characters is truncated to exactly 3000 characters."""
        long_text_content = "PalabraRepetida " * 300  # 4800 characters
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = f"<html><body><p>{long_text_content}</p></body></html>"
        mock_get.return_value = mock_response

        result = visit_place_url("https://www.restaurante-largo.com")

        assert len(result) == 3000
        assert result == ("PalabraRepetida " * 300).strip()[:3000]

    @patch("researcher.services.gemini_service.httpx.get")
    def test_4_visit_place_url_non_200_status_code_returns_fallback_message(self, mock_get):
        """Test that non-200 HTTP responses (e.g. 404, 500) return the fallback failure message."""
        mock_response = MagicMock()
        mock_get.return_value = mock_response

        for status in [404, 500, 403, 502]:
            mock_response.status_code = status
            mock_response.text = "Error Page"
            result = visit_place_url("https://www.error-sitio.com")
            assert result == "No se pudo extraer contenido de la web."

    @patch("researcher.services.gemini_service.httpx.get")
    def test_5_visit_place_url_network_exception_returns_error_message(self, mock_get):
        """Test that exceptions raised by httpx.get are caught and return a descriptive error message."""
        mock_get.side_effect = httpx.ConnectError("Failed to connect to host")
        result = visit_place_url("https://www.unreachable-host.com")
        assert result == "Error al acceder a la web: Failed to connect to host"

        mock_get.side_effect = httpx.TimeoutException("Read timeout after 8.0s")
        result = visit_place_url("https://www.timeout-host.com")
        assert result == "Error al acceder a la web: Read timeout after 8.0s"

    @patch("researcher.services.gemini_service.httpx.get")
    def test_6_visit_place_url_supports_both_http_and_https_prefixes(self, mock_get):
        """Test that both http:// and https:// URLs are accepted and fetched properly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Menu de degustacion</p></body></html>"
        mock_get.return_value = mock_response

        res_http = visit_place_url("http://www.barejemplo.com")
        assert res_http == "Menu de degustacion"

        res_https = visit_place_url("https://www.barejemplo.com")
        assert res_https == "Menu de degustacion"
        assert mock_get.call_count == 2


# =====================================================================
# Tests for classification_agent
# =====================================================================
class Test1ClassificationAgent:
    """Test suite for the classification_agent function."""

    @patch("researcher.services.gemini_service.time.sleep")
    @patch("researcher.services.gemini_service.client")
    def test_0_classification_agent_success_with_clean_json(
        self, mock_client, mock_sleep, sample_places
    ):
        """Test successful classification with clean JSON response returned by the Gemini agent."""
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tier": "Tier 1",
            "motivo": "Alta cocina de producto y setas selectas",
        })
        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        result = classification_agent(sample_places)

        assert len(result) == 1
        assert result[0]["Tier"] == "Tier 1"
        assert result[0]["Motivo agente"] == "Alta cocina de producto y setas selectas"
        mock_sleep.assert_called_once_with(60)
        mock_client.chats.create.assert_called_once()
        mock_chat.send_message.assert_called_once()

    @patch("researcher.services.gemini_service.time.sleep")
    @patch("researcher.services.gemini_service.client")
    def test_1_classification_agent_success_with_markdown_code_block_json(
        self, mock_client, mock_sleep, sample_places
    ):
        """Test classification when response is wrapped in markdown code blocks with '```json' marker."""
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = (
            "```json\n"
            "{\n"
            '  "tier": "Tier 2",\n'
            '  "motivo": "Bistro tradicional con menu cuidado"\n'
            "}\n"
            "```"
        )
        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        result = classification_agent(sample_places)

        assert result[0]["Tier"] == "Tier 2"
        assert result[0]["Motivo agente"] == "Bistro tradicional con menu cuidado"
        mock_sleep.assert_called_once_with(60)

    @patch("researcher.services.gemini_service.time.sleep")
    @patch("researcher.services.gemini_service.client")
    def test_2_classification_agent_success_with_markdown_code_block_without_json_tag(
        self, mock_client, mock_sleep, sample_places
    ):
        """Test classification when response is wrapped in markdown code blocks without 'json' tag ('```')."""
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = (
            "```\n"
            "{\n"
            '  "tier": "Tier 3",\n'
            '  "motivo": "Bar de tapas sencillo con raciones basicas"\n'
            "}\n"
            "```"
        )
        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        result = classification_agent(sample_places)

        assert result[0]["Tier"] == "Tier 3"
        assert result[0]["Motivo agente"] == "Bar de tapas sencillo con raciones basicas"
        mock_sleep.assert_called_once_with(60)

    @patch("researcher.services.gemini_service.time.sleep")
    @patch("researcher.services.gemini_service.client")
    def test_3_classification_agent_api_exception_sets_error_tier(
        self, mock_client, mock_sleep, sample_places
    ):
        """Test that Gemini API exceptions set Tier to 'Error' and record the exception message."""
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = Exception("Google API quota exhausted (429)")
        mock_client.chats.create.return_value = mock_chat

        result = classification_agent(sample_places)

        assert result[0]["Tier"] == "Error"
        assert result[0]["Motivo agente"] == "Google API quota exhausted (429)"
        mock_sleep.assert_called_once_with(60)

    @patch("researcher.services.gemini_service.time.sleep")
    @patch("researcher.services.gemini_service.client")
    def test_4_classification_agent_invalid_json_sets_error_tier(
        self, mock_client, mock_sleep, sample_places
    ):
        """Test that invalid non-JSON response from the agent is caught and Tier is set to 'Error'."""
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Lo siento, no pude analizar el restaurante."
        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        result = classification_agent(sample_places)

        assert result[0]["Tier"] == "Error"
        assert "Expecting value" in result[0]["Motivo agente"]
        mock_sleep.assert_called_once_with(60)

    @patch("researcher.services.gemini_service.time.sleep")
    @patch("researcher.services.gemini_service.client")
    def test_5_classification_agent_missing_json_keys_sets_error_tier(
        self, mock_client, mock_sleep, sample_places
    ):
        """Test that response JSON missing the required 'tier' key causes KeyError handled as Tier='Error'."""
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({"nivel": "Tier 1", "motivo": "Falta clave tier"})
        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        result = classification_agent(sample_places)

        assert result[0]["Tier"] == "Error"
        assert "'tier'" in result[0]["Motivo agente"]
        mock_sleep.assert_called_once_with(60)

    @patch("researcher.services.gemini_service.time.sleep")
    @patch("researcher.services.gemini_service.client")
    def test_6_classification_agent_calls_time_sleep_with_60_seconds(
        self, mock_client, mock_sleep, sample_places
    ):
        """Test that time.sleep is explicitly called with 60 to respect rate limits between iterations."""
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tier": "Tier 1",
            "motivo": "Excelente restaurante",
        })
        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        classification_agent(sample_places)

        mock_sleep.assert_called_once_with(60)

    @patch("researcher.services.gemini_service.time.sleep")
    @patch("researcher.services.gemini_service.client")
    def test_7_classification_agent_annotates_details_dict_and_preserves_existing_keys(
        self, mock_client, mock_sleep
    ):
        """Test that details dict is annotated with 'Tier' and 'Motivo agente' while preserving all existing keys."""
        place_data = {
            "Nombre": "El Bulli",
            "Web": "https://elbulli.com",
            "Precio (nivel Google)": "PRICE_LEVEL_VERY_EXPENSIVE",
            "Dirección": "Cala Montjoi, Roses",
            "Teléfono": "+34 972 61 40 03",
            "Place ID": "ChIJxyz789",
            "Consulta": "Restaurantes alta cocina",
        }
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tier": "Tier 1",
            "motivo": "Referente historico de alta cocina",
        })
        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        result = classification_agent([place_data])

        assert result[0]["Nombre"] == "El Bulli"
        assert result[0]["Dirección"] == "Cala Montjoi, Roses"
        assert result[0]["Teléfono"] == "+34 972 61 40 03"
        assert result[0]["Place ID"] == "ChIJxyz789"
        assert result[0]["Consulta"] == "Restaurantes alta cocina"
        assert result[0]["Tier"] == "Tier 1"
        assert result[0]["Motivo agente"] == "Referente historico de alta cocina"

    @patch("researcher.services.gemini_service.time.sleep")
    @patch("researcher.services.gemini_service.client")
    def test_8_classification_agent_empty_list_returns_empty_list(
        self, mock_client, mock_sleep
    ):
        """Test that passing an empty list to classification_agent returns None without calling Gemini or sleep."""
        result = classification_agent([])

        assert result == []
        mock_client.chats.create.assert_not_called()
        mock_sleep.assert_not_called()

    @patch("researcher.services.gemini_service.time.sleep")
    @patch("researcher.services.gemini_service.client")
    @patch("researcher.services.gemini_service.settings", mock_settings_dict)
    def test_9_classification_agent_formats_prompt_correctly(
        self, mock_client, mock_sleep, sample_places
    ):
        """Test that the prompt sent to chat.send_message formats restaurant name, web, and price."""
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({"tier": "Tier 1", "motivo": "Excelente"})
        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        classification_agent(sample_places)

        expected_prompt = mock_settings_dict["gemini"]["PROMPT_TEMPLATE"].format(
            sample_places[0]["Nombre"],
            sample_places[0]["Web"],
            sample_places[0]["Precio (nivel Google)"],
        )
        mock_chat.send_message.assert_called_once_with(expected_prompt)

    @patch("researcher.services.gemini_service.time.sleep")
    @patch("researcher.services.gemini_service.client")
    @patch("researcher.services.gemini_service.settings", mock_settings_dict)
    def test_10_classification_agent_creates_chat_with_expected_model_and_tool(
        self, mock_client, mock_sleep, sample_places
    ):
        """Test that client.chats.create is called with the model from settings and visit_place_url tool."""
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({"tier": "Tier 1", "motivo": "Muy bueno"})
        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        classification_agent(sample_places)

        mock_client.chats.create.assert_called_once()
        _, kwargs = mock_client.chats.create.call_args
        assert kwargs["model"] == mock_settings_dict["gemini"]["MODEL"]
        assert "config" in kwargs
