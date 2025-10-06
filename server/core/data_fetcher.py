import requests
from .. import config

CWA_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/"

def get_cwa_township_forecast_data():
    """
    Fetches 36-hour weather forecast data for all townships in Taiwan from the CWA API.
    """
    dataset_id = "F-D0047-091"
    url = f"{CWA_API_URL}{dataset_id}"
    params = {"Authorization": config.CWA_API_KEY}
    
    try:
        print("Fetching CWA township forecast data...")
        response = requests.get(url, params=params, verify=getattr(config, "REQUESTS_VERIFY_SSL", True))
        response.raise_for_status()
        print("Successfully fetched CWA data.")
        return response.json()
    except requests.exceptions.SSLError as e:
        print(f"SSL error fetching CWA township data: {e}")
        if getattr(config, "ALLOW_INSECURE_FALLBACK", False):
            try:
                print("Retrying CWA township request with verify=False (insecure fallback)...")
                response = requests.get(url, params=params, verify=False)
                response.raise_for_status()
                print("Successfully fetched CWA data (insecure fallback).")
                return response.json()
            except requests.exceptions.RequestException as e2:
                print(f"Fallback request failed: {e2}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching CWA township data: {e}")
        return None

def get_cwa_county_forecast_data():
    """
    Fetches 36-hour weather forecast data for all counties in Taiwan from the CWA API.
    """
    dataset_id = "F-C0032-001"
    url = f"{CWA_API_URL}{dataset_id}"
    params = {"Authorization": config.CWA_API_KEY}
    
    try:
        print("Fetching CWA county forecast data...")
        response = requests.get(url, params=params, verify=getattr(config, "REQUESTS_VERIFY_SSL", True))
        response.raise_for_status()
        print("Successfully fetched CWA county data.")
        return response.json()
    except requests.exceptions.SSLError as e:
        print(f"SSL error fetching CWA county data: {e}")
        if getattr(config, "ALLOW_INSECURE_FALLBACK", False):
            try:
                print("Retrying CWA county request with verify=False (insecure fallback)...")
                response = requests.get(url, params=params, verify=False)
                response.raise_for_status()
                print("Successfully fetched CWA county data (insecure fallback).")
                return response.json()
            except requests.exceptions.RequestException as e2:
                print(f"Fallback request failed: {e2}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching CWA county data: {e}")
        return None