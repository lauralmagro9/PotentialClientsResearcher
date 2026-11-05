# Potential Clients Researcher (`researcher`)

[![Python Version](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/)
[![Package Manager](https://img.shields.io/badge/poetry-package%20manager-blueviolet.svg)](https://python-poetry.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A smart B2B lead generation tool that helps you quickly identify and assess potential customers for your business in a given area. It discovers relevant establishments through Google Places, uses Google Gemini AI to analyse their websites and assess their business potential, and generates organised Excel reports with prioritised leads.

---

## Key Features

- **Google Places API (New) Search**: Queries places by municipality, province, and establishment type with full pagination and strict category filtering (only restaurants and food establishments).
- **Autonomous Gemini AI Agent**: Leverages Google Gemini (`gemini-3.1-flash-lite` or custom models) with custom function calling (`visit_place_url`). The agent visits each venue's website, parses menu and culinary style, and classifies the prospect into commercial tiers (e.g., Tier 1 Gourmet/Alta Cocina, Tier 2 Tradicional/Bistró, Tier 3 Bar de tapas).
- **Styled Excel Reports**: Generates professional spreadsheets using `openpyxl`, featuring:
  - Formatted and colored headers.
  - Auto-filters and frozen top pane.
  - Clickable website hyperlinks.
  - Automatic column width adjustments.
- **Smart Deduplication & Incremental Updates**: Deduplicates places by Google `Place ID` (with name & address fallback) and can append newly found places into existing Excel files without duplicating records.
- **Dynamic Configuration**: Centralized settings via [`settings.toml`](researcher/settings.toml) with environment variable overrides (`<SECTION>_<PROPERTY>`).
- **Comprehensive Test Suite**: 50+ unit, integration, and E2E tests using `pytest`.

---

## Project Architecture

```
PotentialClientsResearcher/
├── pyproject.toml              # Project dependencies and script definitions
├── poetry.lock                 # Locked dependencies
├── app.log                     # Application runtime logs
├── researcher/
│   ├── __init__.py
│   ├── cli.py                  # Click CLI interface and main workflow orchestration
│   ├── config.py               # Settings loader and environment variable resolver
│   ├── settings.toml           # Default configurations, prompt templates, and field masks
│   └── services/
│       ├── __init__.py
│       ├── maps_service.py     # Google Places API client with pagination & rate limiting
│       ├── gemini_service.py   # Gemini AI agent with tool use (HTML web scraper)
│       └── export_service.py   # Excel export, styling, and deduplication logic
└── tests/
    ├── conftest.py
    ├── unit/                   # Unit test suite
    ├── integration/            # Integration tests with API mocks/fixtures
    └── e2e/                    # End-to-end execution tests
```

---

## Prerequisites

- **Python**: `>= 3.14`
- **Poetry**: Modern Python package and dependency manager
- **Google Cloud API Key**: With the **Places API (New)** enabled
- **Google Gemini API Key**: From Google AI Studio

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/lcalmagro/PotentialClientsResearcher.git
cd PotentialClientsResearcher
```

### 2. Install Dependencies

Install the project virtual environment and packages using Poetry:

```bash
poetry install
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_MAPS_API_KEY="your-google-places-api-key"
GEMINI_API_KEY="your-google-gemini-api-key"
```

> **Note**: Any property defined in `researcher/settings.toml` can be overridden by an environment variable matching the pattern `<SECTION>_<PROPERTY>` (uppercase). For example:
> - `GEMINI_MODEL` (e.g., `gemini-2.5-pro` or `gemini-3.1-flash-lite`)
> - `GOOGLE_MAPS_COUNTRY`
> - `GOOGLE_MAPS_LANGUAGE_CODE`

---

## Usage

The CLI script `investigar_potenciales_clientes` is registered in `pyproject.toml`.

### Interactive Mode

Simply run the command without arguments to be prompted interactively:

```bash
poetry run investigar_potenciales_clientes
```

You will be prompted for:
- **Ciudad** (e.g., `Tarifa`)
- **Provincia** (e.g., `Cádiz`)
- **Establecimiento** (e.g., `Restaurantes`)

This command will search in Spain by default. You can change this in the settings.toml.

### Command-Line Arguments Mode

You can supply the parameters directly using CLI options:

```bash
poetry run investigar_potenciales_clientes --city "Algeciras" --province "Cádiz" --local "Restaurantes"
```

#### CLI Options

| Option | Flag | Description | Required |
|---|---|---|---|
| `--city` | `-c` | Target city/municipality name | Yes |
| `--province` | `-p` | Target province or state | Yes |
| `--local` | `-l` | Establishment type (e.g. `Restaurantes`, `Bares`) | Yes |
| `--existing-file` | `-e` | Path to an existing `.xlsx` file to merge and update | No |

### Appending to an Existing File

To search another area or run subsequent queries and accumulate results into the same spreadsheet:

```bash
poetry run investigar_potenciales_clientes \
  --city "Los Barrios" \
  --province "Cádiz" \
  --local "Restaurantes" \
  --existing-file "restaurantes_algeciras_google_maps_search.xlsx"
```

---

## Customizing the AI Qualification Criteria

The prompt template driving the Gemini Agent is located in [`researcher/settings.toml`](researcher/settings.toml) under `[gemini]`.

By default, the agent is configured to qualify hospitality clients for gourmet wild mushrooms:

```toml
[gemini]
API_KEY = ""
MODEL = 'gemini-3.1-flash-lite'
PROMPT_TEMPLATE = """
        Eres un agente comercial experto en hostelería y producto gourmet.
        Tu objetivo es evaluar si el restaurante '{0}' (Web: {1}, clasificación según precio: {2}) es un buen cliente potencial para la venta de setas silvestres, congeladas o deshidratadas de alta calidad.

        Para ello:
        1. Utiliza la herramienta 'visitar_web_restaurante' pasándole la URL '{1}' para leer su propuesta gastronómica.
        2. Basándote en lo que encuentres, en el nombre si la web falla o en la clasificación según el precio de google, clasifícalo estrictamente en uno de estos tres niveles:
           - Tier 1 (Alta Cocina / Gourmet / Producto)
           - Tier 2 (Tradicional / Bistró / Menú cuidado)
           - Tier 3 (Bar de tapas sencillo / Raciones básicas)
        3. Devuelve únicamente un JSON con este formato exacto:
        {
            "tier": "Tier X",
            "motivo": "Explicación breve de por qué encaja o no"
        }
"""
```

You can customize this prompt directly in `settings.toml` or override it via `GEMINI_PROMPT_TEMPLATE` to adapt the tool to any product, service, or evaluation criteria.

---

## Tests

To run the complete unit test suite:

```bash
poetry run pytest tests/unit
```

To run with verbose output:

```bash
poetry run pytest tests/unit -v
```

---
