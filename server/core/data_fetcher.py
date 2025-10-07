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
        city: Optional city name. If provided, fetches data for that city only.
              If None, fetches data for all cities.
    """
    session = create_session()
    verify = getattr(config, "REQUESTS_VERIFY_SSL", True)
    
    if city:
        dataset_id = CWA_TOWNSHIP_CODES.get(city)
        if not dataset_id:
            print(f"Invalid city name: {city}")
            return None
        urls = [(city, f"{CWA_API_URL}{dataset_id}")]
    else:
        # 如果沒有指定城市，獲取所有城市的資料
        urls = [(city, f"{CWA_API_URL}{code}") for city, code in CWA_TOWNSHIP_CODES.items()]

    all_data = []
    for city_name, url in urls:
        try:
            print(f"Fetching CWA township forecast data for {city_name or 'all cities'}...")
            response = session.get(
                url, 
                params={"Authorization": config.CWA_API_KEY},
                verify=certifi.where() if getattr(config, "REQUESTS_VERIFY_SSL", True) else False
            )
            response.raise_for_status()
            data = response.json()
            if data and 'records' in data:
                if 'location' in data['records']:
                    # 對應單一縣市的鄉鎮資料
                    all_data.append({
                        'locations': [{
                            'location': data['records']['location']
                        }]
                    })
                elif 'locations' in data['records']:
                    # 對應多縣市的鄉鎮資料
                    all_data.append(data['records'])
            print(f"Successfully fetched CWA data for {city_name or 'all cities'}.")
        except requests.exceptions.SSLError as e:
            print(f"SSL error fetching CWA township data for {city_name}: {e}")
            if getattr(config, "ALLOW_INSECURE_FALLBACK", False):
                try:
                    print(f"Retrying CWA township request for {city_name} with verify=False...")
                    response = requests.get(url, params={"Authorization": config.CWA_API_KEY}, 
                                         verify=False)
                    response.raise_for_status()
                    data = response.json()
                    if data and 'records' in data:
                        all_data.append(data['records'])
                    print(f"Successfully fetched CWA data for {city_name} (insecure fallback).")
                except requests.exceptions.RequestException as e2:
                    print(f"Fallback request failed for {city_name}: {e2}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching CWA township data for {city_name}: {e}")
    
    if not all_data:
        return None
    
    # 合併所有數據
    return {
        'records': {
            'locations': all_data
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
