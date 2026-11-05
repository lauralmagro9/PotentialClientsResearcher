"""Unit tests for services.export_service module."""

from openpyxl import load_workbook
from unittest.mock import patch
import os

from researcher.services.export_service import load_existing_excel, export_excel, deduplicate_results
from tests.utils import create_excel_file

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
    "Tier",
    "Motivo agente"
]

mock_settings_dict = {
        "export": {
            "HEADERS": DEFAULT_EXPORT_HEADERS,
        }
    }



class Test0LoadExistingExcel:
    """Tests for the load_existing_excel function."""

    def test_0_load_existing_excel_normal(self, tmp_path):
        """Test loading a normal Excel file with valid headers and multiple data rows."""
        filepath = tmp_path / "valid_places.xlsx"
        headers = ["Nombre", "Dirección", "Place ID"]
        rows = [
            ["Restaurante A", "Calle Primera 1", "ChIJ_001"],
            ["Bar B", "Avenida Segunda 2", "ChIJ_002"],
        ]
        create_excel_file(filepath, headers, rows)

        result = load_existing_excel(str(filepath))

        assert len(result) == 2
        assert result[0] == {
            "Nombre": "Restaurante A",
            "Dirección": "Calle Primera 1",
            "Place ID": "ChIJ_001",
        }
        assert result[1] == {
            "Nombre": "Bar B",
            "Dirección": "Avenida Segunda 2",
            "Place ID": "ChIJ_002",
        }

    def test_1_load_existing_excel_empty_file_headers_only(self, tmp_path):
        """Test loading an Excel file containing headers only without any data rows."""
        filepath = tmp_path / "headers_only.xlsx"
        headers = ["Nombre", "Dirección", "Place ID"]
        create_excel_file(filepath, headers, [])

        result = load_existing_excel(str(filepath))

        assert result == []

    def test_2_load_existing_excel_none_cell_values(self, tmp_path):
        """Test that None/empty cell values in rows are properly converted to empty strings."""
        filepath = tmp_path / "with_none_cells.xlsx"
        headers = ["Nombre", "Dirección", "Web", "Place ID"]
        rows = [
            ["Café Central", None, "https://cafecentral.com", None],
            [None, "Plaza Mayor 5", None, "ChIJ_003"],
        ]
        create_excel_file(filepath, headers, rows)

        result = load_existing_excel(str(filepath))

        assert len(result) == 2
        assert result[0] == {
            "Nombre": "Café Central",
            "Dirección": "",
            "Web": "https://cafecentral.com",
            "Place ID": "",
        }
        assert result[1] == {
            "Nombre": "",
            "Dirección": "Plaza Mayor 5",
            "Web": "",
            "Place ID": "ChIJ_003",
        }

    def test_3_load_existing_excel_none_or_empty_headers(self, tmp_path):
        """Test loading an Excel file where header row contains None or empty cells."""
        filepath = tmp_path / "empty_header.xlsx"
        headers = ["Nombre", None, "Place ID"]
        rows = [
            ["Local X", "Calle X 10", "ChIJ_004"],
        ]
        create_excel_file(filepath, headers, rows)

        result = load_existing_excel(str(filepath))

        assert len(result) == 1
        assert result[0] == {
            "Nombre": "Local X",
            "": "Calle X 10",
            "Place ID": "ChIJ_004",
        }

class Test1Deduplication:
    @patch("researcher.services.export_service.settings", mock_settings_dict)
    def test_0_deduplicate_with_existing_file_merging(self, tmp_path):
        """Test that existing file rows are loaded and merged with new rows without data loss."""
        existing_file = tmp_path / "existing_merge.xlsx"
        existing_headers = DEFAULT_EXPORT_HEADERS
        existing_rows_data = [
            ["Restaurante Existente", "Calle Vieja 1", "", "", "", "restaurant", "Tarifa", "ChIJ_exist_01", "Tarifa", "Tier 2", "Motivo"]
        ]
        create_excel_file(existing_file, existing_headers, existing_rows_data)

        new_rows = [
            {
                "Nombre": "Restaurante Nuevo",
                "Dirección": "Calle Nueva 2",
                "Web": "https://nuevo.es",
                "Teléfono": "+34 956 99 99 99",
                "Precio (nivel Google)": "PRICE_LEVEL_MODERATE",
                "Tipo principal": "restaurant",
                "Municipio (si Google lo devuelve)": "Tarifa",
                "Place ID": "ChIJ_new_02",
                "Consulta": "Tarifa",
                "Tier": "Tier 2",
                "Motivo": "Motivo"
            }
        ]

        deduplicated_results = deduplicate_results(
            results=new_rows,
            existing_file=str(existing_file),
        )

        assert isinstance(deduplicated_results, list)
        assert len(deduplicated_results) == 2
        assert deduplicated_results[0]["Nombre"] == "Restaurante Existente"
        assert deduplicated_results[1]["Nombre"] == "Restaurante Nuevo"
        

    @patch("researcher.services.export_service.settings", mock_settings_dict)
    def test_1_export_deduplication_by_place_id(self):
        """Test de-duplication keeps only the first occurrence when multiple rows share Place ID."""
        
        duplicate_rows = [
            {
                "Nombre": "Café Primero",
                "Dirección": "Calle Uno 1",
                "Place ID": "ChIJ_DUPLICATE_PLACE_ID",
            },
            {
                "Nombre": "Café Segundo",
                "Dirección": "Calle Dos 2",
                "Place ID": "ChIJ_DUPLICATE_PLACE_ID",
            },
        ]

        deduplicated_results = deduplicate_results(
            results=duplicate_rows,
            existing_file=None,
        )

        assert isinstance(deduplicated_results, list)
        assert len(deduplicated_results) == 1
        assert deduplicated_results[0]["Nombre"] == "Café Primero"

    @patch("researcher.services.export_service.settings", mock_settings_dict)
    def test_3_export_deduplication_fallback_by_name_and_address(self):
        """Test fallback de-duplication by normalized (Nombre, Dirección) when Place ID is empty."""
        duplicate_rows = [
            {
                "Nombre": "  Tasca La Esquina  ",
                "Dirección": " Calle Real 5, Tarifa ",
                "Place ID": "",
            },
            {
                "Nombre": "tasca la esquina",
                "Dirección": "calle real 5, tarifa",
                "Place ID": None,
            },
            {
                "Nombre": "Tasca La Esquina",
                "Dirección": "Calle Otra 8, Tarifa",
                "Place ID": "",
            },
        ]

        deduplicated_results = deduplicate_results(
                    results=duplicate_rows,
                    existing_file=None,
                )
        
        assert isinstance(deduplicated_results, list)
        assert len(deduplicated_results) == 2
        assert deduplicated_results[0]["Dirección"] == " Calle Real 5, Tarifa "
        assert deduplicated_results[1]["Dirección"] == "Calle Otra 8, Tarifa"


class Test1ExportExcel:
    """Tests for the export_excel function."""

    @patch("researcher.services.export_service.settings", mock_settings_dict)
    def test_0_export_basic_no_existing_file(self, tmp_path, sample_rows):
        """Test basic export without existing file merging and without tier classification."""

        local_type = "restaurantes"
        city = "Tarifa"
        expected_output_file = f"{local_type}_{city}_google_maps_search.xlsx"

        export_excel(
            rows=sample_rows,
            city="Tarifa",
            local_type="restaurantes",
        )

        assert os.path.isfile(expected_output_file)

        wb = load_workbook(expected_output_file)
        try:
            ws = wb.active
            assert ws.title == "Restaurantes"

            # Check header row
            headers = [cell.value for cell in ws[1]]
            assert headers == DEFAULT_EXPORT_HEADERS

            # Check data rows count
            assert ws.max_row == 3

            # Check data row 1
            row_1_values = [cell.value for cell in ws[2]]
            expected_row_1 = [sample_rows[0].get(h, "") for h in DEFAULT_EXPORT_HEADERS]
            assert row_1_values == expected_row_1

            # Check data row 2
            row_2_values = [cell.value for cell in ws[3]]
            expected_row_2 = [sample_rows[1].get(h, "") for h in DEFAULT_EXPORT_HEADERS]
            assert row_2_values == expected_row_2

            # Check sheet view and filter settings
            assert ws.freeze_panes == "A2"
            assert ws.auto_filter.ref == ws.dimensions

            # Check predefined column dimensions
            expected_widths = {
                "A": 32, "B": 48, "C": 38, "D": 22, "E": 24,
                "F": 24, "G": 30, "H": 38, "I": 48,
            }
            for col_letter, width in expected_widths.items():
                assert ws.column_dimensions[col_letter].width == width
        finally:
            wb.close()

    @patch("researcher.services.export_service.settings", mock_settings_dict)
    def test_1_export_hyperlink_creation_for_web_cells(self, tmp_path):
        """Test that cells with Web URLs receive clickable hyperlinks and style while empty ones do not."""
        output_file = tmp_path / "web_links.xlsx"
        rows = [
            {
                "Nombre": "Local Con Web",
                "Web": "https://localconweb.com",
                "Place ID": "ChIJ_web_01",
            },
            {
                "Nombre": "Local Sin Web",
                "Web": "",
                "Place ID": "ChIJ_web_02",
            },
            {
                "Nombre": "Local None Web",
                "Web": None,
                "Place ID": "ChIJ_web_03",
            },
        ]

        export_excel(
            rows=rows,
            city="Tarifa",
            local_type="locales",
            existing_file=str(output_file),
        )

        wb = load_workbook(output_file)
        try:
            ws = wb.active
            # Column 3 is Web
            web_cell_1 = ws.cell(row=2, column=3)
            assert web_cell_1.value == "https://localconweb.com"
            assert web_cell_1.hyperlink is not None
            assert getattr(web_cell_1.hyperlink, "target", str(web_cell_1.hyperlink)) == "https://localconweb.com"
            assert web_cell_1.style == "Hyperlink"

            web_cell_2 = ws.cell(row=3, column=3)
            assert web_cell_2.value == None
            assert web_cell_2.hyperlink is None
            assert web_cell_2.style != "Hyperlink"

            web_cell_3 = ws.cell(row=4, column=3)
            assert web_cell_3.value == None
            assert web_cell_3.hyperlink is None
            assert web_cell_3.style != "Hyperlink"
        finally:
            wb.close()

    @patch("researcher.services.export_service.settings", mock_settings_dict)
    def test_2_export_file_naming_default_vs_existing_file(self, tmp_path, monkeypatch):
        """Test filename logic: default '{local_type}_{city}_google_maps_search.xlsx' vs explicit existing_file."""
        # 1. Default filename generation in current working directory
        monkeypatch.chdir(tmp_path)
        sample_place = [{"Nombre": "Bar Prueba", "Place ID": "ChIJ_prueba_01"}]

        export_excel(
            rows=sample_place,
            city="Tarifa",
            local_type="chiringuitos",
            existing_file=None,
        )
        expected_default_file = tmp_path / "chiringuitos_Tarifa_google_maps_search.xlsx"
        assert expected_default_file.is_file()

        # 2. Explicit existing_file path
        custom_file = tmp_path / "custom_output_name.xlsx"
        export_excel(
            rows=sample_place,
            city="Tarifa",
            local_type="chiringuitos",
            existing_file=str(custom_file),
        )
        assert custom_file.is_file()

    @patch("researcher.services.export_service.settings", mock_settings_dict)
    def test_3_export_header_styling(self, tmp_path):
        """Test that row 1 header cells are styled with bold white font, dark blue fill, and centered alignment."""
        output_file = tmp_path / "header_styling.xlsx"
        rows = [{"Nombre": "Bar Estilo", "Place ID": "ChIJ_style_01"}]

        export_excel(
            rows=rows,
            city="Cadiz",
            local_type="bares",
            existing_file=str(output_file),
        )

        wb = load_workbook(output_file)
        try:
            ws = wb.active
            for cell in ws[1]:
                # Font assertions
                assert cell.font.bold is True
                assert cell.font.color is not None
                font_color = str(getattr(cell.font.color, "rgb", "") or getattr(cell.font.color, "value", ""))
                assert "FFFFFF" in font_color

                # PatternFill assertions
                assert cell.fill.fill_type == "solid"
                fill_color = str(getattr(cell.fill.fgColor, "rgb", "") or getattr(cell.fill.fgColor, "value", ""))
                assert "1F4E78" in fill_color

                # Alignment assertions
                assert cell.alignment.vertical == "center"
                assert cell.alignment.wrap_text is True
        finally:
            wb.close()

    @patch("researcher.services.export_service.settings", mock_settings_dict)
    def test_4_export_with_non_existent_existing_file(self, tmp_path):
        """Test exporting when existing_file parameter is given a non-existent path creates a fresh file."""
        non_existent_file = tmp_path / "new_non_existent.xlsx"
        assert not non_existent_file.exists()

        rows = [{"Nombre": "Local Fresco", "Place ID": "ChIJ_fresh_01"}]

        export_excel(
            rows=rows,
            city="Tarifa",
            local_type="locales",
            existing_file=str(non_existent_file),
        )

        assert non_existent_file.is_file()
        wb = load_workbook(non_existent_file)
        try:
            ws = wb.active
            assert ws.max_row == 2
            assert ws.cell(row=2, column=1).value == "Local Fresco"
        finally:
            wb.close()

    @patch("researcher.services.export_service.settings", mock_settings_dict)
    def test_5_export_with_empty_rows(self, tmp_path):
        """Test that exporting an empty row list creates a valid workbook containing only the headers."""
        output_file = tmp_path / "empty_export.xlsx"

        export_excel(
            rows=[],
            city="Tarifa",
            local_type="restaurantes",
            existing_file=str(output_file),
        )

        assert output_file.is_file()
        wb = load_workbook(output_file)
        try:
            ws = wb.active
            assert ws.max_row == 1
            headers = [cell.value for cell in ws[1]]
            assert headers == DEFAULT_EXPORT_HEADERS
        finally:
            wb.close()
            
    @patch("researcher.services.export_service.settings", mock_settings_dict)
    def test_6_export_with_missing_keys_in_row_dict(self, tmp_path):
        """Test that row dictionaries missing some header keys default to empty strings without error."""
        output_file = tmp_path / "missing_keys.xlsx"
        sparse_row = [
            {"Nombre": "Solo Nombre", "Place ID": "ChIJ_sparse_01"}
        ]

        export_excel(
            rows=sparse_row,
            city="Tarifa",
            local_type="bares",
            existing_file=str(output_file),
        )

        wb = load_workbook(output_file)
        try:
            ws = wb.active
            assert ws.cell(row=2, column=1).value == "Solo Nombre"
            assert ws.cell(row=2, column=2).value == None  # Dirección
            assert ws.cell(row=2, column=3).value == None  # Web
            assert ws.cell(row=2, column=8).value == "ChIJ_sparse_01"  # Place ID
        finally:
            wb.close()
