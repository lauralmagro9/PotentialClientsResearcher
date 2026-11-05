"""Unit tests for researcher.cli module."""

from unittest.mock import patch
import requests
from click.testing import CliRunner

from researcher.cli import (
    investigate_and_export_places,
    investigate_and_export_places_command,
)

mock_settings_dict = {
    "google_maps": {
        "COUNTRY": "España",
    }
}


class Test0InvestigateAndExportPlaces:
    """Tests for investigate_and_export_places."""

    @patch("researcher.cli.time.sleep")
    @patch("researcher.cli.export_excel")
    @patch("researcher.cli.classification_agent")
    @patch("researcher.cli.deduplicate_results")
    @patch("researcher.cli.search_places")
    @patch("researcher.cli.settings", mock_settings_dict)
    def test_0_builds_query_and_exports_results(
        self,
        mock_search,
        mock_dedup,
        mock_agent,
        mock_export,
        mock_sleep,
        capsys,
    ):
        """Search with the built query, deduplicate, classify with agent, and export the returned rows."""
        raw_places = [
            {
                "Nombre": "Restaurante El Faro",
                "Place ID": "ChIJ_faro_001",
            }
        ]
        dedup_places = [
            {
                "Nombre": "Restaurante El Faro",
                "Place ID": "ChIJ_faro_001",
            }
        ]
        tiered_places = [
            {
                "Nombre": "Restaurante El Faro",
                "Place ID": "ChIJ_faro_001",
                "Tier": "Tier 1",
                "Razón agente": "Buena presencia online",
            }
        ]
        mock_search.return_value = raw_places
        mock_dedup.return_value = dedup_places
        mock_agent.return_value = tiered_places

        result = investigate_and_export_places("Tarifa", "Cádiz", "Restaurantes")

        query = "Restaurantes en Tarifa, Cádiz, España"
        mock_search.assert_called_once_with(query)
        mock_dedup.assert_called_once_with(raw_places, None)
        mock_agent.assert_called_once_with(dedup_places)
        mock_export.assert_called_once_with(
            tiered_places, "Tarifa", "Restaurantes", existing_file=None
        )
        mock_sleep.assert_called_once_with(1)
        assert result is None
        captured = capsys.readouterr()
        assert f"Buscando: {query}" in captured.out
        assert "Resultados recibidos: 1" in captured.out

    @patch("researcher.cli.time.sleep")
    @patch("researcher.cli.export_excel")
    @patch("researcher.cli.classification_agent")
    @patch("researcher.cli.deduplicate_results")
    @patch("researcher.cli.search_places")
    @patch("researcher.cli.settings", mock_settings_dict)
    def test_1_empty_results_without_existing_file_skips_export(
        self,
        mock_search,
        mock_dedup,
        mock_agent,
        mock_export,
        mock_sleep,
        capsys,
    ):
        """Skip the export when the search returns nothing and no file is given."""
        mock_search.return_value = []
        mock_dedup.return_value = []
        mock_agent.return_value = []

        result = investigate_and_export_places("Tarifa", "Cádiz", "Restaurantes")

        mock_search.assert_called_once_with("Restaurantes en Tarifa, Cádiz, España")
        mock_dedup.assert_called_once_with([], None)
        mock_agent.assert_called_once_with([])
        mock_export.assert_not_called()
        mock_sleep.assert_called_once_with(1)
        assert result is None
        captured = capsys.readouterr()
        assert "No se han recibido resultados" in captured.out

    @patch("researcher.cli.time.sleep")
    @patch("researcher.cli.export_excel")
    @patch("researcher.cli.classification_agent")
    @patch("researcher.cli.deduplicate_results")
    @patch("researcher.cli.search_places")
    @patch("researcher.cli.settings", mock_settings_dict)
    def test_2_empty_results_with_existing_file_still_exports(
        self,
        mock_search,
        mock_dedup,
        mock_agent,
        mock_export,
        mock_sleep,
    ):
        """Export an empty result list when an existing file is provided."""
        mock_search.return_value = []
        mock_dedup.return_value = []
        mock_agent.return_value = []

        result = investigate_and_export_places(
            "Tarifa", "Cádiz", "Restaurantes", existing_file="clientes.xlsx"
        )

        mock_search.assert_called_once_with("Restaurantes en Tarifa, Cádiz, España")
        mock_dedup.assert_called_once_with([], "clientes.xlsx")
        mock_agent.assert_called_once_with([])
        mock_export.assert_called_once_with(
            [], "Tarifa", "Restaurantes", existing_file="clientes.xlsx"
        )
        mock_sleep.assert_called_once_with(1)
        assert result is None

    @patch("researcher.cli.time.sleep")
    @patch("researcher.cli.export_excel")
    @patch("researcher.cli.classification_agent")
    @patch("researcher.cli.deduplicate_results")
    @patch("researcher.cli.search_places")
    @patch("researcher.cli.settings", mock_settings_dict)
    def test_3_request_exception_without_existing_file_skips_export(
        self,
        mock_search,
        mock_dedup,
        mock_agent,
        mock_export,
        mock_sleep,
        capsys,
    ):
        """Skip the export when the search fails and no existing file is given."""
        mock_search.side_effect = requests.ConnectionError("network down")

        result = investigate_and_export_places("Tarifa", "Cádiz", "Restaurantes")

        mock_dedup.assert_not_called()
        mock_agent.assert_not_called()
        mock_export.assert_not_called()
        mock_sleep.assert_called_once_with(1)
        assert result is None
        captured = capsys.readouterr()
        assert "Error de red/API" in captured.out
        assert "network down" in captured.out
        assert "No se han recibido resultados" in captured.out

    @patch("researcher.cli.time.sleep")
    @patch("researcher.cli.export_excel")
    @patch("researcher.cli.classification_agent")
    @patch("researcher.cli.deduplicate_results")
    @patch("researcher.cli.search_places")
    @patch("researcher.cli.settings", mock_settings_dict)
    def test_4_request_exception_with_existing_file_exports_empty_rows(
        self,
        mock_search,
        mock_dedup,
        mock_agent,
        mock_export,
        mock_sleep,
    ):
        """Export an empty list when the search fails but an existing file is given."""
        mock_search.side_effect = requests.HTTPError("429")

        result = investigate_and_export_places(
            "Tarifa", "Cádiz", "Restaurantes", existing_file="clientes.xlsx"
        )

        mock_dedup.assert_not_called()
        mock_agent.assert_not_called()
        mock_export.assert_called_once_with(
            [], "Tarifa", "Restaurantes", existing_file="clientes.xlsx"
        )
        mock_sleep.assert_called_once_with(1)
        assert result is None

    @patch("researcher.cli.time.sleep")
    @patch("researcher.cli.export_excel")
    @patch("researcher.cli.classification_agent")
    @patch("researcher.cli.deduplicate_results")
    @patch("researcher.cli.search_places")
    @patch("researcher.cli.settings", mock_settings_dict)
    def test_5_deduplication_filters_before_classification(
        self,
        mock_search,
        mock_dedup,
        mock_agent,
        mock_export,
        mock_sleep,
    ):
        """Verify that deduplicate_results filters raw places before passing to classification_agent."""
        raw_places = [
            {"Nombre": "Bar Uno", "Place ID": "ChIJ_01"},
            {"Nombre": "Bar Uno Duplicado", "Place ID": "ChIJ_01"},
        ]
        dedup_places = [
            {"Nombre": "Bar Uno", "Place ID": "ChIJ_01"}
        ]
        tiered_places = [
            {"Nombre": "Bar Uno", "Place ID": "ChIJ_01", "Tier": "Tier 2", "Razón agente": "Sin web"}
        ]
        mock_search.return_value = raw_places
        mock_dedup.return_value = dedup_places
        mock_agent.return_value = tiered_places

        investigate_and_export_places(
            "Conil", "Cádiz", "Bares", existing_file="previo.xlsx"
        )

        mock_dedup.assert_called_once_with(raw_places, "previo.xlsx")
        mock_agent.assert_called_once_with(dedup_places)
        mock_export.assert_called_once_with(
            tiered_places, "Conil", "Bares", existing_file="previo.xlsx"
        )


class Test1InvestigateAndExportPlacesCommand:
    """Tests for the Click CLI command investigate_and_export_places_command."""

    @patch("researcher.cli.investigate_and_export_places")
    def test_0_command_passes_options_to_investigate_function(
        self, mock_investigate
    ):
        """Invoke Click command with options and verify investigate_and_export_places is called."""
        runner = CliRunner()
        result = runner.invoke(
            investigate_and_export_places_command,
            ["--city", "Tarifa", "--province", "Cádiz", "--local", "Restaurantes"],
        )

        assert result.exit_code == 0
        mock_investigate.assert_called_once_with(
            "Tarifa", "Cádiz", "Restaurantes", None
        )

    @patch("researcher.cli.investigate_and_export_places")
    def test_1_command_with_existing_file(self, mock_investigate, tmp_path):
        """Invoke Click command with --existing-file pointing to an existing file."""
        existing_file = tmp_path / "existente.xlsx"
        existing_file.touch()

        runner = CliRunner()
        result = runner.invoke(
            investigate_and_export_places_command,
            [
                "--city", "Tarifa",
                "--province", "Cádiz",
                "--local", "Restaurantes",
                "--existing-file", str(existing_file),
            ],
        )

        assert result.exit_code == 0
        mock_investigate.assert_called_once_with(
            "Tarifa", "Cádiz", "Restaurantes", str(existing_file)
        )
