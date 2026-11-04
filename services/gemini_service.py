import pandas as pd
import httpx
import json
import time
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from config import settings


# Initialise client
gemini_api_key = settings["gemini"]["GEMINI_API_KEY"]
client = genai.Client(api_key=gemini_api_key)

# ---------------------------------------------------------
# 1. Define the tool that the agent can use
# ---------------------------------------------------------
def visit_place_url(url: str) -> str:
    """Visit a restaurant's website and extract its main text content for cuisine analysis.

    Fetches the page at the given URL, strips non-content elements
    (scripts, styles, navigation, footer), and returns the first 3 000
    characters of visible text.

    Args:
        url: The restaurant website URL to visit.

    Returns:
        A string with the extracted text content, or an error/status
        message if the URL is invalid or the request fails.
    """
    if not url or pd.isna(url) or not str(url).startswith(('http://', 'https://')):
        return "No hay URL válida disponible."
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = httpx.get(url, headers=headers, timeout=8.0, follow_redirects=True)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for s in soup(["script", "style", "nav", "footer"]):
                s.extract()
            return ' '.join(soup.get_text().split())[:3000]  # First 3000 characters
    except Exception as e:
        return f"Error al acceder a la web: {str(e)}"
    
    return "No se pudo extraer contenido de la web."

# ---------------------------------------------------------
# 2. Load the Excel data and run the classification agent
# ---------------------------------------------------------
def classification_agent(places_details: list[dict]) -> list[dict]:
    """Classify a list of restaurant places into quality tiers using the Gemini agent.

    Iterates over each place, sends a classification prompt to the Gemini
    model (which may autonomously browse the restaurant's website via the
    ``visitar_web_restaurante`` tool), and annotates each dictionary with
    the resulting ``Tier`` and ``Razón agente`` fields.

    A 60-second delay is enforced between API calls to respect rate limits.

    Args:
        places_details: List of dictionaries, each containing at least
            ``Nombre``, ``Web``, and ``Precio (nivel Google)`` keys.

    Returns:
        list[dict]: The same list with ``Tier`` and ``Razón agente``
        fields added to each entry.
    """
    print("🤖 Iniciando el agente de clasificación...\n")
    n_places = len(places_details)

    # Iterate row by row (row 1 is the header, so data starts at row 2)
    for i, details in enumerate(places_details):
        
        nombre = details['Nombre']
        web = details['Web']
        price_category = details['Precio (nivel Google)']
            
        print(f"[{i+1}/{n_places}] Analizando a fondo: {nombre} ({web})")
        prompt_agent = settings["gemini"]["PROMPT_TEMPLATE"].format(nombre, web, price_category)
        model=settings["gemini"]["MODEL"]
        
        try:
            chat = client.chats.create(
                model=model,
                config=types.GenerateContentConfig(
                    tools=[visit_place_url],
                    temperature=0.1
                )
            )
            
            response = chat.send_message(prompt_agent)
            response_text = response.text.strip()
            
            # Strip markdown code-block wrappers if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            response_json = json.loads(response_text)
            tier = response_json["tier"]
            reason = response_json["motivo"]
            
            print(f"-> Clasificado: {tier}\n")
            
        except Exception as e:
            print(f"Error procesando {nombre}: {e}\n")
            tier = "Error"
            reason = str(e)

        # Add classification data to the place details
        details['Tier'] = tier
        details['Motivo agente'] = reason

        time.sleep(60)

        return places_details