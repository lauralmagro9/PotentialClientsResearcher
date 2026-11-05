from openpyxl import Workbook

def create_excel_file(filepath, headers: list, rows: list) -> None:
    """Helper utility to write a minimal real Excel file for test fixtures."""
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(filepath)
    wb.close()