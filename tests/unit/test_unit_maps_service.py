"""Unit tests for services.maps_service module."""

import sys
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from researcher.services.maps_service import get_component, search_places

mock_settings_dict = {
    "google_maps": {
        "API_KEY": "fake-api-key",
        "URL": "https://places.googleapis.com/v1/places:searchText",
        "FIELD_MASK": ["places.id", "places.displayName"],
        "REGION_CODE": "ES",
        "LANGUAGE_CODE": "es",
    }
}


class Test0GetComponent:
    """Tests for the get_component helper function."""

    def test_0_extract_matching_component(self):
        """Extract a specific address component when a matching type exists."""
        place = {
            "addressComponents": [
                {"longText": "Tarifa", "types": ["locality", "political"]},
                {"longText": "Cádiz", "types": ["administrative_area_level_2", "political"]},
            ]
        }
        result = get_component(place, "locality")
        assert result == "Tarifa"

    def test_1_component_not_found(self):
        """Return an empty string when the requested component type is not present."""
        place = {
            "addressComponents": [
                {"longText": "Cádiz", "types": ["administrative_area_level_2", "political"]},
            ]
        }
        result = get_component(place, "locality")
        assert result == ""

    def test_2_address_components_missing(self):
        """Return an empty string when addressComponents is missing or empty."""
        place_empty = {}
        place_with_empty_list = {"addressComponents": []}

        assert get_component(place_empty, "locality") == ""
        assert get_component(place_with_empty_list, "locality") == ""

    def test_3_multiple_components_first_matching_wins(self):
        """Return the longText of the first matching component when multiple components match."""
        place = {
            "addressComponents": [
                {"longText": "First Match", "types": ["locality"]},
                {"longText": "Second Match", "types": ["locality"]},
            ]
        }
        result = get_component(place, "locality")
        assert result == "First Match"


class Test1SearchPlaces:
    """Tests for the search_places API querying and filtering function."""

    @patch("researcher.services.maps_service.settings", mock_settings_dict)
    def test_0_basic_single_page_success(self, mock_post, sample_restaurant):
        """Process a basic single-page API response with restaurant results and expected mapping."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "places": [sample_restaurant],
        }
        mock_post.return_value = mock_response

        query = "Restaurantes en Tarifa"
        rows = search_places(query)

        mock_post.assert_called_once_with(
            "https://places.googleapis.com/v1/places:searchText",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": "fake-api-key",
                "X-Goog-FieldMask": "places.id,places.displayName",
            },
            json={
                "textQuery": query,
                "pageSize": 20,
                "languageCode": "es",
                "regionCode": "ES",
            },
            timeout=40,
        )
        mock_response.raise_for_status.assert_called_once()

        assert len(rows) == 1
        assert rows[0] == {
            "Nombre": "Restaurante El Faro",
            "Dirección": "Calle Mayor 1, Tarifa",
            "Web": "https://elfaro.es",
            "Teléfono": "+34 956 00 00 00",
            "Precio (nivel Google)": "PRICE_LEVEL_MODERATE",
            "Tipo principal": "restaurant",
            "Municipio (si Google lo devuelve)": "Tarifa",
            "Place ID": "place_123",
            "Consulta": query,
        }

    @patch("researcher.services.maps_service.settings", mock_settings_dict)
    def test_1_filtering_skips_non_restaurant_food(self, mock_post):
        """Skip places that do not have 'restaurant' or 'food' in types and whose primaryType is not 'restaurant'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "places": [
                {
                    "id": "hotel_1",
                    "displayName": {"text": "Hotel Playa"},
                    "primaryType": "lodging",
                    "types": ["lodging", "point_of_interest"],
                },
                {
                    "id": "shop_1",
                    "displayName": {"text": "Surf Shop"},
                    "primaryType": "clothing_store",
                    "types": ["store", "point_of_interest"],
                },
            ]
        }
        mock_post.return_value = mock_response

        rows = search_places("Hoteles y tiendas")
        assert rows == []

    @patch("researcher.services.maps_service.settings", mock_settings_dict)
    def test_2_filtering_includes_primary_type_restaurant(self, mock_post):
        """Include a place if primaryType is 'restaurant' even without 'restaurant' in types."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "places": [
                {
                    "id": "tapas_bar",
                    "displayName": {"text": "Tapas El Puerto"},
                    "primaryType": "restaurant",
                    "types": ["bar", "point_of_interest"],
                }
            ]
        }
        mock_post.return_value = mock_response

        rows = search_places("Tapas")
        assert len(rows) == 1
        assert rows[0]["Nombre"] == "Tapas El Puerto"
        assert rows[0]["Tipo principal"] == "restaurant"

    @patch("researcher.services.maps_service.settings", mock_settings_dict)
    def test_3_filtering_includes_food_in_types(self, mock_post):
        """Include a place if 'food' is present in types even without 'restaurant' in types or primaryType."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "places": [
                {
                    "id": "cafe_1",
                    "displayName": {"text": "Cafetería Central"},
                    "primaryType": "cafe",
                    "types": ["cafe", "food", "point_of_interest"],
                }
            ]
        }
        mock_post.return_value = mock_response

        rows = search_places("Cafeterías")
        assert len(rows) == 1
        assert rows[0]["Nombre"] == "Cafetería Central"

    @patch("researcher.services.maps_service.settings", mock_settings_dict)
    def test_4_pagination_triggers_second_request(self, mock_post):
        """Trigger a second request when nextPageToken is present, passing pageToken in payload."""
        resp_page1 = MagicMock()
        resp_page1.status_code = 200
        resp_page1.json.return_value = {
            "places": [
                {
                    "id": "p1",
                    "displayName": {"text": "Restaurante Uno"},
                    "types": ["restaurant"],
                }
            ],
            "nextPageToken": "token_page_2",
        }

        resp_page2 = MagicMock()
        resp_page2.status_code = 200
        resp_page2.json.return_value = {
            "places": [
                {
                    "id": "p2",
                    "displayName": {"text": "Restaurante Dos"},
                    "types": ["restaurant"],
                }
            ],
            "nextPageToken": None,
        }

        mock_post.side_effect = [resp_page1, resp_page2]

        rows = search_places("Restaurantes")

        assert len(rows) == 2
        assert rows[0]["Place ID"] == "p1"
        assert rows[1]["Place ID"] == "p2"
        assert mock_post.call_count == 2

        # Verify pageToken is absent in first call payload and present in second call payload
        first_call_payload = mock_post.call_args_list[0].kwargs["json"]
        assert "pageToken" not in first_call_payload

        second_call_payload = mock_post.call_args_list[1].kwargs["json"]
        assert second_call_payload["pageToken"] == "token_page_2"

    @patch("researcher.services.maps_service.settings", mock_settings_dict)
    def test_5_http_429_raises_runtime_error(self, mock_post):
        """Raise RuntimeError with descriptive message when HTTP status 429 rate limit occurs."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        with pytest.raises(
            RuntimeError,
            match="Google ha limitado temporalmente las solicitudes \\(429\\)",
        ):
            search_places("Restaurantes")

    @patch("researcher.services.maps_service.settings", mock_settings_dict)
    def test_6_http_error_raises_requests_http_error(self, mock_post):
        """Raise requests.HTTPError when response.raise_for_status() encounters an HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "500 Internal Server Error"
        )
        mock_post.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            search_places("Restaurantes")

    @patch("researcher.services.maps_service.settings", mock_settings_dict)
    def test_7_phone_number_fallback(self, mock_post):
        """Fallback from internationalPhoneNumber to nationalPhoneNumber, or empty string if neither."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "places": [
                {
                    "id": "p1",
                    "displayName": {"text": "Both phones"},
                    "types": ["restaurant"],
                    "internationalPhoneNumber": "+34 956 11 22 33",
                    "nationalPhoneNumber": "956 11 22 33",
                },
                {
                    "id": "p2",
                    "displayName": {"text": "National phone only"},
                    "types": ["restaurant"],
                    "internationalPhoneNumber": None,
                    "nationalPhoneNumber": "956 44 55 66",
                },
                {
                    "id": "p3",
                    "displayName": {"text": "No phone"},
                    "types": ["restaurant"],
                },
            ]
        }
        mock_post.return_value = mock_response

        rows = search_places("Restaurantes")
        assert len(rows) == 3
        assert rows[0]["Teléfono"] == "+34 956 11 22 33"
        assert rows[1]["Teléfono"] == "956 44 55 66"
        assert rows[2]["Teléfono"] == ""

    @patch("researcher.services.maps_service.settings", mock_settings_dict)
    def test_8_municipality_fallback_chain(self, mock_post):
        """Follow municipality fallback chain: locality -> postal_town -> administrative_area_level_2."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "places": [
                {
                    "id": "p1",
                    "displayName": {"text": "Has locality"},
                    "types": ["restaurant"],
                    "addressComponents": [
                        {"longText": "Tarifa", "types": ["locality"]},
                        {"longText": "Postal Town 1", "types": ["postal_town"]},
                        {"longText": "Cádiz", "types": ["administrative_area_level_2"]},
                    ],
                },
                {
                    "id": "p2",
                    "displayName": {"text": "Has postal_town only"},
                    "types": ["restaurant"],
                    "addressComponents": [
                        {"longText": "Los Barrios", "types": ["postal_town"]},
                        {"longText": "Cádiz", "types": ["administrative_area_level_2"]},
                    ],
                },
                {
                    "id": "p3",
                    "displayName": {"text": "Has administrative_area_level_2 only"},
                    "types": ["restaurant"],
                    "addressComponents": [
                        {"longText": "Cádiz", "types": ["administrative_area_level_2"]},
                    ],
                },
                {
                    "id": "p4",
                    "displayName": {"text": "Has none"},
                    "types": ["restaurant"],
                    "addressComponents": [
                        {"longText": "España", "types": ["country"]},
                    ],
                },
            ]
        }
        mock_post.return_value = mock_response

        rows = search_places("Restaurantes")
        assert len(rows) == 4
        assert rows[0]["Municipio (si Google lo devuelve)"] == "Tarifa"
        assert rows[1]["Municipio (si Google lo devuelve)"] == "Los Barrios"
        assert rows[2]["Municipio (si Google lo devuelve)"] == "Cádiz"
        assert rows[3]["Municipio (si Google lo devuelve)"] == ""

    @patch("researcher.services.maps_service.settings", mock_settings_dict)
    def test_9_time_sleep_called_between_pages(self, mock_post, mock_sleep):
        """Verify time.sleep is called with 2 seconds between pages during pagination."""
        resp_page1 = MagicMock()
        resp_page1.status_code = 200
        resp_page1.json.return_value = {
            "places": [{"id": "p1", "displayName": {"text": "P1"}, "types": ["restaurant"]}],
            "nextPageToken": "token_2",
        }

        resp_page2 = MagicMock()
        resp_page2.status_code = 200
        resp_page2.json.return_value = {
            "places": [{"id": "p2", "displayName": {"text": "P2"}, "types": ["restaurant"]}],
            "nextPageToken": "token_3",
        }

        resp_page3 = MagicMock()
        resp_page3.status_code = 200
        resp_page3.json.return_value = {
            "places": [{"id": "p3", "displayName": {"text": "P3"}, "types": ["restaurant"]}],
            "nextPageToken": None,
        }

        mock_post.side_effect = [resp_page1, resp_page2, resp_page3]

        search_places("Restaurantes")

        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(2), call(2)])
