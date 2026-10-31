"""Weather data from Open-Meteo (CC BY 4.0), turned into the Risk Engine's format.

Every fetch_* function returns the raw API JSON so it can be saved as a snapshot;
every parse_* function turns raw JSON into engine types, so tests run offline.
"""

ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"
