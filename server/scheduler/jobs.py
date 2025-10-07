from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core import data_fetcher, calculation, json_generator
from core import image_analyzer
from core import image_url_resolver
import config
from services import fcm_sender, discord_sender
import asyncio

scheduler = AsyncIOScheduler()

# --- Data Cache ---
# 初始化全局變數
if 'CACHED_WEATHER_DATA' not in globals():
    CACHED_WEATHER_DATA = {
        'county_weather': {},      # 縣市天氣資料
        'township_weather': {},    # 鄉鎮天氣資料
        'qpf_data': {},           # 降雨強度資料
        'aqi_data': {},           # 空氣品質資料
        'update_time': None       # 最後更新時間
    }

if 'CACHED_CWA_TOWNSHIP_DATA' not in globals():
    CACHED_CWA_TOWNSHIP_DATA = None

if 'CACHED_TOWNSHIP_MAP' not in globals():
    CACHED_TOWNSHIP_MAP = {}

if 'CACHED_IMAGE_METRICS' not in globals():
    CACHED_IMAGE_METRICS = {}

# 更新時間間隔設定（6點和12點）
UPDATE_HOURS = [6, 12]
# --- End of Cache ---

def _normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    # Normalize common variants and whitespace
    return name.replace("台", "臺").replace(" ", "").strip()

async def _fetch_weather_data(county_data=None):
    """Fetches both county and township level weather data."""
    if county_data is None:
        # 如果沒有提供縣市資料，則獲取它
        county_data = await asyncio.to_thread(data_fetcher.get_cwa_county_forecast_data)

    # --- DEBUGGING: Inspect raw county_data ---
    if county_data and isinstance(county_data, dict):
        print(f"Debug: county_data keys: {county_data.keys()}")
        records = county_data.get('records', {})
        locations = records.get('location', [])
        print(f"Debug: Found {len(locations)} locations in county_data.")
    else:
        print("Debug: county_data is None or not a dict.")
    # --- END DEBUGGING ---

    # 獲取所有縣市的鄉鎮級資料
    township_data_tasks = []
    for city in data_fetcher.CWA_TOWNSHIP_CODES.keys():
        township_data_tasks.append(
            asyncio.to_thread(data_fetcher.get_cwa_township_forecast_data, city)
        )
    
    # 並行獲取所有鄉鎮資料
    township_data_results = await asyncio.gather(*township_data_tasks)
    
    # 合併所有鄉鎮資料
    print(f"Debug: Merging {len(township_data_results)} results from township API calls.")
    all_locations = []
    for i, result in enumerate(township_data_results):
        if result and isinstance(result, dict) and result.get('records') and isinstance(result['records'], dict) and result['records'].get('location'):
            all_locations.extend(result['records']['location'])
        else:
            # Log the unexpected structure
            print(f"Debug: Result {i} has an unexpected structure.")
            if result and isinstance(result, dict):
                print(f"Debug: Result {i} keys: {result.keys()}")
                if 'records' in result and isinstance(result['records'], dict):
                    print(f"Debug: Result {i}['records'] keys: {result['records'].keys()}")
            else:
                print(f"Debug: Result {i} is not a valid dictionary: {result}")

    print(f"Debug: Total locations collected after merge: {len(all_locations)}")
    all_township_data = {
        'records': {
            'location': all_locations
        }
    }
    
    # 處理縣市資料
    county_weather = {}
    if county_data and 'records' in county_data:
        for location in county_data['records'].get('location', []):
            county_name = location.get('locationName')
            print(f"Debug: Processing county: {county_name}")
            if county_name:
                weather_elements = {}
                for element in location.get('weatherElement', []):
                    name = element.get('elementName')
                    if name and element.get('time'):
                        param = element['time'][0].get('parameter', {})
                        weather_elements[name] = param.get('parameterName')
                
                county_weather[county_name] = {
                    'temperature': weather_elements.get('T'),
                    'weather_description': weather_elements.get('Wx'),
                    'pop': weather_elements.get('PoP')
                }
    
    # 處理鄉鎮資料
    township_weather = {}
    if all_township_data and all_township_data.get('records') and all_township_data['records'].get('location'):
        for location in all_township_data['records']['location']:
            township_name = location.get('locationName')
            if township_name:
                # Store the entire location object, as this is what calculation.py expects
                township_weather[_normalize_name(township_name)] = location
    
    return county_weather, township_weather, all_township_data

async def fetch_data_job():
    """
    Scheduled job to fetch and cache weather data.
    """
    print("Running scheduled job: fetch_data_job")
    global CACHED_WEATHER_DATA, CACHED_IMAGE_METRICS, CACHED_CWA_TOWNSHIP_DATA, CACHED_TOWNSHIP_MAP

    try:
        # 獲取API數據
        county_data = await asyncio.to_thread(data_fetcher.get_cwa_county_forecast_data)
        weather_data = await _fetch_weather_data(county_data)
        
        if not weather_data:
            print("Failed to fetch weather data")
            return
        
        county_weather, township_weather, all_township_data = weather_data
        
        # 更新快取資料
        CACHED_CWA_TOWNSHIP_DATA = all_township_data
        CACHED_TOWNSHIP_MAP = township_weather
        CACHED_WEATHER_DATA.update({
                'county_weather': county_weather,
                'township_weather': township_weather
            })
    except Exception as e:
        print(f"Error in fetch_data_job while fetching weather data: {e}")
        return
    
    # 分析圖片數據
    try:
        if config.TESSERACT_CMD:
            image_analyzer.configure_tesseract_cmd(config.TESSERACT_CMD)

        # Resolve image URLs
        qpf12_url = await asyncio.to_thread(
            image_url_resolver.resolve_latest_url, config.POP12_URL_PATTERNS
        )
        qpf6_url = await asyncio.to_thread(
            image_url_resolver.resolve_latest_url, config.POP6_URL_PATTERNS
        )
        aqi_url = await asyncio.to_thread(
            image_url_resolver.resolve_latest_url, config.AQI_URL_PATTERNS
        )

        # --- Consolidated Image Metric Analysis ---
        image_metrics = {}
        if not (config.IMAGE_SAMPLE_COORDS):
             print("Warning: IMAGE_SAMPLE_COORDS not configured in config.py. Skipping image analysis.")
             return

        for county, sample_xy in config.IMAGE_SAMPLE_COORDS.items():
            if not sample_xy:
                continue

            # Analyze QPF (Rainfall Intensity)
            qpf12 = await asyncio.to_thread(
                image_analyzer.analyze_qpf_from_image, qpf12_url, sample_xy
            ) if qpf12_url else None
            qpf6 = await asyncio.to_thread(
                image_analyzer.analyze_qpf_from_image, qpf6_url, sample_xy
            ) if qpf6_url else None

            # Analyze AQI
            aqi_level = None
            if aqi_url:
                box_size = 10
                x, y = sample_xy
                sample_box = (x - box_size // 2, y - box_size // 2, x + box_size // 2, y + box_size // 2)
                aqi_level = await asyncio.to_thread(
                    image_analyzer.analyze_aqi_from_image, aqi_url, sample_box
                )

            image_metrics[county] = {
                "qpf12_mm_per_hr": qpf12,
                "qpf6_mm_per_hr": qpf6,
                "aqi_level": aqi_level,
            }
        
        # Update the single, consolidated cache for image metrics
        CACHED_IMAGE_METRICS.clear()
        CACHED_IMAGE_METRICS.update(image_metrics)
        
        # Deprecated caches are no longer updated
        # CACHED_WEATHER_DATA.update({ 'qpf_data': {}, 'aqi_data': {} })
        # global QPF_CACHE_BY_COUNTY; QPF_CACHE_BY_COUNTY = {}

        print(f"Image analysis complete. Metrics cached for {len(image_metrics)} counties.")

    except Exception as e:
        print(f"Error analyzing images: {e}")

    if CACHED_CWA_TOWNSHIP_DATA:
        print("Scheduled job finished. CWA data has been cached.")
        # After fetching data, generate the final JSON output
        global CACHED_FINAL_JSON
        CACHED_FINAL_JSON = json_generator.generate_json_output()
        print(f"Debug: township_weather map contains {len(township_weather)} entries.")
        # After fetching data, check if any notifications need to be sent.
        await check_and_send_notifications()
    else:
        print("Scheduled job finished. CWA data fetching failed.")

async def check_and_send_notifications():
    """
    Checks for notification conditions based on the cached CWA data.
    """
    print("Checking for notification conditions...")
    # Example: A user is subscribed to notifications for "臺北市中正區"
    user_township = "臺北市中正區"
    user_device_token = "DEVICE_TOKEN_HERE" # This would come from a database

    # This part will be updated to use the new map via the calculation function
    forecast = calculation.get_forecast_for_township(user_township, CACHED_TOWNSHIP_MAP)

    if forecast and forecast["cwa_forecast"]["chance_of_rain_12h"]:
        pop_value_str = forecast["cwa_forecast"]["chance_of_rain_12h"]
        if pop_value_str and pop_value_str.isdigit():
            pop_value = int(pop_value_str)
            if pop_value > 50: # Condition: chance of rain > 50%
                message = f"Weather Alert for {user_township}: Chance of rain is {pop_value}% in the next 12 hours."
                print(message)
                
                # Send to Discord
                discord_sender.send_to_discord(message)

                # Send FCM push notification (placeholder)
                # fcm_sender.send_notification(
                #      title=f"{user_township} Weather Alert",
                #      body=message,
                #      token=user_device_token
                # )

# Schedule the data fetching job to run twice daily at 06:00 and 12:00
scheduler.add_job(fetch_data_job, 'cron', hour='6,12', minute=0)

# --- Getter functions for API endpoints to access cached data ---
def get_cached_weather_data():
    """獲取快取的天氣資料"""
    return CACHED_WEATHER_DATA

def get_county_weather(county_name: str):
    """獲取指定縣市的天氣資料"""
    return CACHED_WEATHER_DATA['county_weather'].get(county_name)

def get_township_weather(township_name: str):
    """獲取指定鄉鎮的天氣資料"""
    return CACHED_WEATHER_DATA['township_weather'].get(township_name)

def get_qpf_data(county_name: str):
    """獲取指定縣市的降雨強度資料"""
    return CACHED_WEATHER_DATA['qpf_data'].get(county_name)

def get_aqi_data(county_name: str):
    """獲取指定縣市的空氣品質資料"""
    return CACHED_WEATHER_DATA['aqi_data'].get(county_name)

def get_last_update_time():
    """獲取資料最後更新時間"""
    return CACHED_WEATHER_DATA['update_time']
