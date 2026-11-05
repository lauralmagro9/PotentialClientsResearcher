"""Integration tests for services.maps_service against the Google Places API."""

from researcher.services.maps_service import search_places


class Test0SearchPlaces:
    """Tests for search_places against the live Google Places API."""

    def test_0_search_places_returns_restaurant_rows(self):
        """Verify that a known restaurant query returns mapped place rows."""
        query = "Restaurante El Faro Tarifa, Cádiz, España"
        rows = search_places(query)

        assert isinstance(rows, list)
        assert rows

        row = rows[0]
        assert row["Consulta"] == query
        assert row["Nombre"]
        assert row["Dirección"]
        assert row["Place ID"]
        assert row["Tipo principal"]
        assert "Tarifa" in (
            row["Dirección"] + row["Municipio (si Google lo devuelve)"]
        )
