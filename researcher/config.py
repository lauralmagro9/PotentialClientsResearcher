import os
import sys
import tomllib
import logging
from typing import Any
from dotenv import load_dotenv

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('PotentialClientsResearcher')

SETTINGS_FILE: str = "settings.toml"
SETTINGS_PATH: str = os.path.join(os.path.dirname(__file__), SETTINGS_FILE)

def get_config():
    """Load application settings from the TOML configuration file.

    Reads the settings file and, for each property, checks whether a
    corresponding environment variable exists (formatted as
    ``<SERVICE>_<PROPERTY>`` in upper-case).  Environment variables take
    precedence over file defaults.  If a property has an empty default
    and no environment variable is set, a ``ValueError`` is raised.

    Returns:
        dict: Nested dictionary of configuration settings keyed by service name.

    Raises:
        ValueError: If a required environment variable is missing and no
            default value is provided.
    """
    # Load environment variables
    load_dotenv()
    
    with open(SETTINGS_PATH, "rb") as fp:
        settings = tomllib.load(fp)

    for service, properties in settings.items():
        for property, default_value in properties.items():
            environment_key = f"{service}_{property}".upper()
            if environment_key not in os.environ and default_value == "":
                raise ValueError(f"Environment variable {environment_key} is not set and no default value is provided")
            else:
                settings[service][property] = os.getenv(environment_key, default=default_value)

    return settings

settings = get_config()