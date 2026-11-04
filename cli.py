import click
import time
import requests
from config import settings
from services.maps_service import search_places
from services.export_service import export_excel


def investigate_and_export_places(city:str, province:str, local_type:str, existing_file:str=None):
    """Search for places and export the results to an Excel file.

    Builds a search query from the given location parameters, calls
    :func:`search_places` to retrieve matching results, and delegates to
    :func:`export_excel` to write the output.

    Args:
        city (str): Target city name.
        province (str): Province or state name.
        country (str): Country name.
        local_type (str): Type of establishment to search for (e.g. ``"Restaurante"``).
        existing_file: Optional path to an existing Excel file to merge
            new results into.
    """
    all_rows = []
    country = settings["google_maps"]["COUNTRY"]
    query = f"{local_type} en {city}, {province}, {country}"
    print(f"Buscando: {query}")
    try:
        results = search_places(query)
        print(f"  Resultados recibidos: {len(results)}")
        all_rows.extend(results)
    except requests.RequestException as exc:
        print(f"Error de red/API en '{query}': {exc}")
    time.sleep(1)

    if not all_rows and not existing_file:
        print(
            "No se han recibido resultados. Comprueba la clave API, "
            "la facturación y que Places API (New) esté habilitada."
        )
        return

    export_excel(all_rows, city, local_type, existing_file=existing_file)


@click.command("investigate_potetial_clients")
@click.argument('city', prompt='Ciudad', type=str, help='Ciudad de búsqueda.')
@click.argument('province', prompt='Provincia', type=str, help='Provincia de búsqueda.')
@click.argument('local', prompt='Establecimiento', type=str, help='Tipo de establecimiento.')
@click.option('--existing-file', default=None, type=click.Path(exists=True), help='Archivo existente en el que guardar nuevos resultados.')
def search_and_export_places_command(city, province, local, existing_file):
    """Search for places in a given city using the Google Maps API and export results to Excel.

    Accepts a CITY, PROVINCE and LOCAL arguments to customise the search query and an existing_file option to save the results.
    """
    click.echo(investigate_and_export_places(city, province, local, existing_file))

if __name__ == '__main__':
    search_and_export_places_command(city="Algeciras", province="Cádiz", local_type="Restaurantes", existing_file=None)