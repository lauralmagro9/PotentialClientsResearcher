import os
from researcher.cli import investigate_and_export_places

def test_investigate_and_export_places_command():
    city = "Catellar"
    province = "Cádiz"
    local = "Restaurantes"
    existing_file = None
    investigate_and_export_places(city, province, local, existing_file)
    exp_filename = existing_file if existing_file else f"{local}_{city}_google_maps_search.xlsx".lower().replace(' ', '_')
    assert os.path.exists(exp_filename)