from unittest.mock import patch
import pytest


DEFAULT_EXPORT_HEADERS = [
    "Nombre",
    "Dirección",
    "Web",
    "Teléfono",
    "Precio (nivel Google)",
    "Tipo principal",
    "Municipio (si Google lo devuelve)",
    "Place ID",
    "Consulta",
]


@pytest.fixture
def sample_rows():
    """Fixture providing representative place data rows."""
    return [
        {
            "Nombre": "Restaurante El Faro",
            "Dirección": "Calle Mayor 10, Tarifa",
            "Web": "https://elfarotarifa.com",
            "Teléfono": "+34 956 00 00 01",
            "Precio (nivel Google)": "PRICE_LEVEL_MODERATE",
            "Tipo principal": "restaurant",
            "Municipio (si Google lo devuelve)": "Tarifa",
            "Place ID": "ChIJ_faro_001",
            "Consulta": "Restaurantes en Tarifa",
            "Tier": "Tier 1",
            "Motivo agente": "motivo"
        },
        {
            "Nombre": "Bar El Tapeo",
            "Dirección": "Avenida Andalucía 20, Tarifa",
            "Web": None,
            "Teléfono": "+34 956 00 00 02",
            "Precio (nivel Google)": "PRICE_LEVEL_INEXPENSIVE",
            "Tipo principal": "bar",
            "Municipio (si Google lo devuelve)": "Tarifa",
            "Place ID": "ChIJ_tapeo_002",
            "Consulta": "Restaurantes en Tarifa",
            "Tier": "Tier 1",
            "Motivo agente": "motivo"
        },
    ]



# @pytest.fixture(autouse=True)
# def mock_export_settings():
#     """Patch services.export_service.settings with fresh export HEADERS for each test.

#     Uses deepcopy to prevent list mutations (e.g. headers.extend) from leaking
#     between individual test executions.
#     """
#     settings_dict = {
#         "export": {
#             "HEADERS": copy.deepcopy(DEFAULT_EXPORT_HEADERS),
#         }
#     }
#     with patch("services.export_service.settings", settings_dict):
#         yield settings_dict


@pytest.fixture
def sample_place():
    """Fixture providing a sample restaurant place dictionary."""
    return {
        "Nombre": "El Celler de Can Roca",
        "Web": "https://cellercanroca.com",
        "Precio (nivel Google)": "PRICE_LEVEL_VERY_EXPENSIVE",
        "Dirección": "Can Sunyer, 48, 17007 Girona",
        "Teléfono": "+34 972 40 67 00",
        "Place ID": "ChIJceller123",
        "Consulta": "Restaurantes Girona",
    }


@pytest.fixture
def sample_places(sample_place):
    """Fixture providing a list containing a single restaurant place dictionary."""
    return [sample_place.copy()]


@pytest.fixture
def mock_html_content():
    return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Restaurante Asador</title>
            <style>
                body { font-family: sans-serif; color: #333; }
                .nav-menu { display: flex; }
            </style>
            <script>
                window.dataLayer = window.dataLayer || [];
                console.log("analytics initialized");
            </script>
        </head>
        <body>
            <nav>
                <ul>
                    <li><a href="#inicio">Inicio</a></li>
                    <li><a href="#carta">Nuestra Carta</a></li>
                </ul>
            </nav>
            <h1>Asador El Roble</h1>
            <p>Especialidad en carnes maduradas y setas silvestres de temporada.</p>
            <script type="text/javascript">
                var token = "secret_12345";
            </script>
            <footer>
                <p>Todos los derechos reservados 2026. Contacto: 912345678</p>
            </footer>
        </body>
        </html>
        """

@pytest.fixture(autouse=True)
def mock_sleep():
    """Patch time.sleep across all tests to prevent actual delays."""
    with patch("services.maps_service.time.sleep") as mock_s:
        yield mock_s


@pytest.fixture
def mock_post():
    """Patch requests.post for search_places API calls."""
    with patch("services.maps_service.requests.post") as mock_p:
        yield mock_p


@pytest.fixture
def sample_restaurant():
    """Provide a standard dictionary representing a restaurant place from Google Places API."""
    return {
        "id": "place_123",
        "displayName": {"text": "Restaurante El Faro"},
        "formattedAddress": "Calle Mayor 1, Tarifa",
        "websiteUri": "https://elfaro.es",
        "internationalPhoneNumber": "+34 956 00 00 00",
        "nationalPhoneNumber": "956 00 00 00",
        "priceLevel": "PRICE_LEVEL_MODERATE",
        "primaryType": "restaurant",
        "types": ["restaurant", "food", "point_of_interest"],
        "addressComponents": [
            {"longText": "Tarifa", "types": ["locality", "political"]},
            {"longText": "Cádiz", "types": ["administrative_area_level_2", "political"]},
        ],
    }