import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import config
import json

CWA_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/"

# API 端點設定
CWA_COUNTY_FORECAST_ID = "F-C0032-001"    # 縣市天氣預報-一般天氣預報
CWA_TOWNSHIP_CODES = {
    # 北部地區
    "宜蘭縣": "F-D0047-001",
    "桃園市": "F-D0047-005",
    "新竹縣": "F-D0047-009",
    "苗栗縣": "F-D0047-013",
    "彰化縣": "F-D0047-017",
    "南投縣": "F-D0047-021",
    "雲林縣": "F-D0047-025",
    "嘉義縣": "F-D0047-029",
    "屏東縣": "F-D0047-033",
    "臺東縣": "F-D0047-037",
    "花蓮縣": "F-D0047-041",
    "澎湖縣": "F-D0047-045",
    "基隆市": "F-D0047-049",
    "新竹市": "F-D0047-053",
    "嘉義市": "F-D0047-057",
    "臺北市": "F-D0047-061",
    "高雄市": "F-D0047-065",
    "新北市": "F-D0047-069",
    "臺中市": "F-D0047-073",
    "臺南市": "F-D0047-077",
    "連江縣": "F-D0047-081",
    "金門縣": "F-D0047-085"
}

def create_session():
    """Creates a requests session with retry mechanism."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount('http://', HTTPAdapter(max_retries=retry))
    session.mount('https://', HTTPAdapter(max_retries=retry))
    return session

def get_cwa_township_forecast_data(city: str):
    """
    Fetches township weather forecast data for a specific city.
    """
    session = create_session()
    dataset_id = CWA_TOWNSHIP_CODES.get(city)
    if not dataset_id:
        print(f"Invalid city name: {city}")
        return None

    url = f"{CWA_API_URL}{dataset_id}"
    all_locations = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    params = {
        "Authorization": config.CWA_API_KEY,
    }

    try:
        print(f"Fetching CWA township forecast data for {city}...")
        response = session.get(
            url,
            params=params,
            headers=headers,
            verify=certifi.where() if getattr(config, "REQUESTS_VERIFY_SSL", True) else False
        )
        response.raise_for_status()

        try:
            data = response.json()
            records = data.get('records', {})
            
            location_groups = records.get('Locations', records.get('locations'))
            if isinstance(location_groups, list):
                for loc_group in location_groups:
                    if isinstance(loc_group, dict):
                        locations = loc_group.get('Location', loc_group.get('location'))
                        if isinstance(locations, list):
                            all_locations.extend(locations)
            elif 'location' in records:
                 all_locations.extend(records['location'])

            print(f"Successfully fetched and parsed CWA data for {city}. Found {len(all_locations)} locations.")

        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"CRITICAL: Failed to decode or parse JSON for {city}. Error: {e}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"CRITICAL: Error fetching CWA township data for {city}. Error: {e}")
        return None

    if not all_locations:
        print(f"Warning: No locations found for {city} after successful fetch.")
        return None

    return {
        'records': {
            'location': all_locations
        }
    }

def get_cwa_county_forecast_data():
    """
    Fetches 36-hour weather forecast data for all counties in Taiwan from the CWA API.
    """
    session = create_session()
    url = f"{CWA_API_URL}{CWA_COUNTY_FORECAST_ID}"
    params = {"Authorization": config.CWA_API_KEY, "elementName": "MinT,MaxT,Wx,PoP"}
    verify = getattr(config, "REQUESTS_VERIFY_SSL", True)
    
    try:
        print("Fetching CWA county forecast data...")
        response = session.get(url, params=params, verify=verify)
        response.raise_for_status()
        print("Successfully fetched CWA county data.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching CWA county data: {e}")
        return None
