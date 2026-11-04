import os
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from config import settings

def load_existing_excel(filepath:str) -> list[dict]:
    """Load an existing Excel file and return its rows as a list of dictionaries.

    Each dictionary maps the header name to the corresponding cell value
    for that row.  Empty cells are represented as empty strings.

    Args:
        filepath (str): Path to the ``.xlsx`` file to read.

    Returns:
        list[dict]: One dictionary per data row, keyed by column header.
    """
    wb = load_workbook(filepath, read_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h) if h else "" for h in next(rows_iter)]
    existing = []
    for row in rows_iter:
        existing.append(dict(zip(headers, [v if v is not None else "" for v in row])))
    wb.close()
    return existing


def export_excel(rows:list[dict], city:str, local_type:str, tier_classification:str, existing_file:str=None):
    """Export place data to a styled Excel workbook.

    Merges *rows* with any previously exported rows found in
    *existing_file*, de-duplicates by Place ID (or by name + address as
    fallback), and writes the result to an ``.xlsx`` file with formatted
    headers, frozen panes, auto-filters, and clickable website links.

    Args:
        rows (list[dict]): List of dictionaries containing the new place data.
        city (str): City name used to build the default output filename.
        local_type (str): Establishment type used to build the default output filename.
        tier_classification (str): If truthy, ``Tier`` and ``Motivo`` columns
            are appended to the header list.
        existing_file (str): Optional path to an existing Excel file whose rows
            will be merged with *rows* before writing. Default is none.
    """
    headers = settings["export"]["HEADERS"]
    if tier_classification:
        headers.extend(["Tier", "Motivo agente"])

    # If an existing Excel file is provided, load its rows first.
    all_rows = []
    if existing_file and os.path.isfile(existing_file):
        existing_rows = load_existing_excel(existing_file)
        all_rows.extend(existing_rows)
        print(f"Filas cargadas del Excel existente: {len(existing_rows)}")
    all_rows.extend(rows)

    # De-duplicate by Place ID, keeping the first occurrence.
    unique = {}
    for row in all_rows:
        key = row.get("Place ID") or (
            row.get("Nombre", "").strip().lower(),
            row.get("Dirección", "").strip().lower()
        )
        unique.setdefault(key, row)

    wb = Workbook()
    ws = wb.active
    ws.title = local_type.title()
    ws.append(headers)

    for row in unique.values():
        ws.append([row.get(h, "") for h in headers])

    header_fill = PatternFill("solid", fgColor="1F4E78")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    widths = {
        "A": 32, "B": 48, "C": 38, "D": 22, "E": 24,
        "F": 24, "G": 30, "H": 38, "I": 48,
    }
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    # Make website cells clickable when they contain a URL.
    for row_idx in range(2, ws.max_row + 1):
        web_cell = ws.cell(row=row_idx, column=3)
        if web_cell.value:
            web_cell.hyperlink = web_cell.value
            web_cell.style = "Hyperlink"

    filename = existing_file if existing_file else f"{local_type}_{city}_google_maps_search.xlsx"
    wb.save(filename)
    print(f"Excel guardado en: {os.path.abspath(filename)}")
    print(f"Lugares exportados (sin duplicados): {len(unique)}")
    new_count = len(unique) - (len(all_rows) - len(rows))
    if existing_file:
        print(f"{local_type.title()} añadidos: {max(0, new_count)}")