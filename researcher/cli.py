import click
import time
import requests
from researcher.config import settings
from researcher.services.maps_service import search_places
from researcher.services.gemini_service import classification_agent
from researcher.services.export_service import export_excel, deduplicate_results


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
    country = settings["google_maps"]["COUNTRY"]
    query = f"{local_type} en {city}, {province}, {country}"
    print(f"Buscando: {query}")

    places_tiered = []
    try:
        places_details = search_places(query)
        print(f"  Resultados recibidos: {len(places_details)}")
        deduplicated_places_details = deduplicate_results(places_details, existing_file)
        places_tiered = classification_agent(deduplicated_places_details)

    except requests.RequestException as exc:
        print(f"Error de red/API en '{query}': {exc}")
    time.sleep(1)

    if not places_tiered and not existing_file:
        print(
            "No se han recibido resultados. Comprueba la clave API, "
            "la facturación y que Places API (New) esté habilitada."
        )
        return

    export_excel(places_tiered, city, local_type, existing_file=existing_file)


@click.command("investigate_potetial_clients")
@click.option('--city', prompt='Ciudad', required=True, type=str, help='Ciudad de búsqueda.')
@click.option('--province', prompt='Provincia', required=True, type=str, help='Provincia de búsqueda.')
@click.option('--local', prompt='Establecimiento', required=True, type=str, help='Tipo de establecimiento.')
@click.option('--existing-file', default=None, required=False, type=click.Path(exists=True), help='Archivo existente en el que guardar nuevos resultados.')
def investigate_and_export_places_command(city, province, local, existing_file):
    """Search for places in a given city using the Google Maps API and export results to Excel.

    Accepts a CITY, PROVINCE and LOCAL options to customise the search query and an existing_file option to save the results.
    """
    click.echo(investigate_and_export_places(city, province, local, existing_file))