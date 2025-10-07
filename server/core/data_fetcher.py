import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import config

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

def get_cwa_township_forecast_data(city: str = None):
    """
    Fetches 36-hour weather forecast data for townships.
    Args:
        city: The city name to fetch data for.
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
        "elementName": "PoP12h,T,Wx,PoP6h"
    }

    try:
        print(f"Fetching CWA township forecast data for {city}...")
        response = session.get(
            url, 
            params=params,
            headers=headers, # Add User-Agent header
            verify=certifi.where() if getattr(config, "REQUESTS_VERIFY_SSL", True) else False
        )
        response.raise_for_status()
        
        # --- FINAL DEBUG: Print raw response text ---
        print(f"--- Raw Response for {city} ---")
        print(response.text)
        print("--- End Raw Response ---")

        import json

        # Manually decode the response to avoid potential encoding issues with response.json()
        try:
            data_text = response.content.decode('utf-8')
            data = json.loads(data_text)

            records = data.get('records', {})
            # The F-D0047-XXX responses have a nested structure: records -> locations (list of groups) -> location (list of towns)
            if 'locations' in records:
                for location_group in records['locations']:
                    if location_group.get('location'):
                        all_locations.extend(location_group['location'])
            # Fallback for a flatter structure, just in case
            elif 'location' in records:
                all_locations.extend(records['location'])
            
            print(f"Successfully fetched and parsed CWA data for {city}. Found {len(all_locations)} locations in this batch.")

        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"CRITICAL: Failed to decode or parse JSON for {city}. Error: {e}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"CRITICAL: Error fetching CWA township data for {city}. Error: {e}")
        return None # Fail fast

    if not all_locations:
        print(f"Warning: No locations found for {city} after successful fetch.")
        return None

    # Return the standard structure for this single city
    return {
        'records': {
            'location': all_locations
        }
    }

CWA_TOWNSHIP_FORECAST_ID = "F-D0047-093"  # 鄉鎮天氣預報



def get_cwa_county_forecast_data():
    """
    Fetches 36-hour weather forecast data for all counties in Taiwan from the CWA API.
    """
    session = create_session()
    url = f"{CWA_API_URL}{CWA_COUNTY_FORECAST_ID}"
    params = {"Authorization": config.CWA_API_KEY}
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
