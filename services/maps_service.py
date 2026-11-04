"""
Query restaurants via the Google Places API (New) and export results to Excel.

IMPORTANT:
- Review the Google Places API terms before using or retaining results.
- This script exports the received fields to a working Excel file. It does not
  assume that Google permits indefinite retention of all those fields.
- Set GOOGLE_MAPS_API_KEY as an environment variable.
- Requires: pip install requests openpyxl
"""

import time
import requests
from config import settings


def get_component(place: dict, component_type: str) -> str:
    """Extract a specific address component from a Google Places result.

    Iterates over the ``addressComponents`` list of the place and returns
    the ``longText`` value for the first component whose ``types`` list
    contains *component_type*.

    Args:
        place (dict): A dictionary representing a single Google Places result.
        component_type (str): The address-component type to look for (e.g.
            ``"locality"``, ``"postal_town"``).

    Returns:
        str: The component's ``longText`` value, or an empty string if
        the component type is not found.
    """
    for component in place.get("addressComponents", []):
        if component_type in component.get("types", []):
            return component.get("longText")
    return ""

def search_places(query: str) -> list[dict]:
    """Search for places matching a text query using the Google Places API.

    Sends a ``searchText`` request and automatically paginates through
    all available result pages.  Only results whose ``types`` include
    ``restaurant`` or ``food`` (or whose ``primaryType`` is
    ``restaurant``) are kept.

    Args:
        query: Free-text search string (e.g. ``"Restaurantes en Tarifa"``).

    Returns:
        list[dict]: A list of dictionaries, one per matching place, with
        keys corresponding to the export headers defined in settings.

    Raises:
        RuntimeError: If the API returns HTTP 429 (rate-limited).
        requests.HTTPError: For any other non-2xx response status.
    """
    rows = []
    page_token = None
    headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": settings["google_maps"]["API_KEY"],
    "X-Goog-FieldMask": ",".join(settings["google_maps"]["FIELD_MASK"]),
    }
    query_url = settings["google_maps"]["URL"]
    region_code = settings["google_maps"]["REGION_CODE"]
    language_code = settings["google_maps"]["LANGUAGE_CODE"]

    while True:
        payload = {
            "textQuery": query,
            "pageSize": 20,
            "languageCode": language_code,
            "regionCode": region_code,
        }
        if page_token:
            payload["pageToken"] = page_token

        response = requests.post(
            query_url, headers=headers, json=payload, timeout=40
        )

        if response.status_code == 429:
            raise RuntimeError(
                "Google ha limitado temporalmente las solicitudes (429). "
                "Espera antes de volver a intentarlo."
            )
        response.raise_for_status()
        data = response.json()

        for place in data.get("places", []):
            name = place.get("displayName", {}).get("text", "")
            types = place.get("types", [])
            # Skip results that are clearly not restaurants.
            if not (
                "restaurant" in types
                or place.get("primaryType") == "restaurant"
                or "food" in types
            ):
                continue

            rows.append({
                "Nombre": name,
                "Dirección": place.get("formattedAddress", ""),
                "Web": place.get("websiteUri", ""),
                "Teléfono": (
                    place.get("internationalPhoneNumber")
                    or place.get("nationalPhoneNumber", "")
                ),
                "Precio (nivel Google)": place.get("priceLevel", ""),
                "Tipo principal": place.get("primaryType", ""),
                "Municipio (si Google lo devuelve)": (
                    get_component(place, "locality")
                    or get_component(place, "postal_town")
                    or get_component(place, "administrative_area_level_2")
                ),
                "Place ID": place.get("id", ""),
                "Consulta": query,
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(2)

    return rows


