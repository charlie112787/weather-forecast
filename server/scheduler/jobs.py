from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core import data_fetcher, calculation, json_generator
from core import image_analyzer
from core import image_url_resolver
import config
from services import fcm_sender, discord_sender
import asyncio
import datetime
import os
import json

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
        county_data = await asyncio.to_thread(data_fetcher.get_cwa_county_forecast_data)

    if county_data and isinstance(county_data, dict):
        print(f"Debug: county_data keys: {county_data.keys()}")
        records = county_data.get('records', {})
        locations = records.get('location', [])
        print(f"Debug: Found {len(locations)} locations in county_data.")
    else:
        print("Debug: county_data is None or not a dict.")

    cities = list(data_fetcher.CWA_TOWNSHIP_CODES.keys())
    township_data_tasks = []
    for city in cities:
        township_data_tasks.append(
            asyncio.to_thread(data_fetcher.get_cwa_township_forecast_data, city)
        )
    
    township_data_results = await asyncio.gather(*township_data_tasks)
    
    all_locations = []
    township_weather = {}
    for i, result in enumerate(township_data_results):
        city_name = cities[i]
        if result and isinstance(result, dict) and result.get('records') and result['records'].get('location'):
            locations = result['records']['location']
            all_locations.extend(locations)
            for location in locations:
                township_name = location.get('LocationName')
                if township_name:
                    full_name = f"{city_name}{township_name}"
                    normalized_name = _normalize_name(full_name)
                    township_weather[normalized_name] = location

    all_township_data = {
        'records': {
            'location': all_locations
        }
    }
    
    county_weather = {}
    if county_data and 'records' in county_data:
        for location in county_data['records'].get('location', []):
            county_name = location.get('locationName')
            if county_name:
                weather_elements = {}
                min_temp, max_temp = None, None
                for element in location.get('weatherElement', []):
                    name = element.get('elementName')
                    if name and element.get('time'):
                        param = element['time'][0].get('parameter', {})
                        weather_elements[name] = param.get('parameterName')
                        if name == 'MinT':
                            min_temp = int(param.get('parameterName'))
                        if name == 'MaxT':
                            max_temp = int(param.get('parameterName'))
                if min_temp is not None and max_temp is not None:
                    weather_elements['T'] = (min_temp + max_temp) // 2
                
                county_weather[county_name] = weather_elements
    
    return county_weather, township_weather, all_township_data

async def fetch_data_job():
    """
    Scheduled job to fetch and cache weather data.
    """
    print("Running scheduled job: fetch_data_job")
    global CACHED_WEATHER_DATA, CACHED_IMAGE_METRICS, CACHED_CWA_TOWNSHIP_DATA, CACHED_TOWNSHIP_MAP, CACHED_FINAL_JSON

    try:
        # Fetch all data concurrently
        results = await asyncio.gather(
            asyncio.to_thread(data_fetcher.get_cwa_county_forecast_data),
            asyncio.to_thread(data_fetcher.get_cwa_qpf_data)
        )
        county_data, qpf_data = results

        weather_data = await _fetch_weather_data(county_data)
        
        if not weather_data or not weather_data[1]:
            print("Failed to fetch weather data or township_weather is empty")
            return
        
        county_weather, township_weather, all_township_data = weather_data
        
        CACHED_CWA_TOWNSHIP_DATA = all_township_data
        CACHED_TOWNSHIP_MAP = township_weather
        CACHED_WEATHER_DATA.update({
            'county_weather': county_weather,
            'township_weather': township_weather,
            'qpf_data': qpf_data,  # Cache the QPF data
            'update_time': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Error in fetch_data_job while fetching weather data: {e}")
        return
    
    try:
        if config.TESSERACT_CMD:
            image_analyzer.configure_tesseract_cmd(config.TESSERACT_CMD)

        # Resolve image URLs
        pop12_url = await asyncio.to_thread(image_url_resolver.resolve_latest_url, config.POP12_URL_PATTERNS)
        pop6_url = await asyncio.to_thread(image_url_resolver.resolve_latest_url, config.POP6_URL_PATTERNS)
        daily_rain_url = image_url_resolver.resolve_ncdr_daily_rain_url()
        nowcast_base_url = await asyncio.to_thread(image_url_resolver.resolve_latest_url, config.NCDR_NOWCAST_URL_PATTERN)
        aqi_url = await asyncio.to_thread(image_url_resolver.resolve_latest_url, config.AQI_URL_PATTERNS)

        image_metrics = {}
        if not (config.IMAGE_SAMPLE_COORDS):
             print("Warning: IMAGE_SAMPLE_COORDS not configured in config.py. Skipping image analysis.")
             return

        for county, sample_xy in config.IMAGE_SAMPLE_COORDS.items():
            if not sample_xy:
                continue

            # Analyze PoP12 and PoP6
            pop12_data = await asyncio.to_thread(
                image_analyzer.analyze_qpf_from_image, pop12_url, sample_xy
            ) if pop12_url else None
            pop6_data = await asyncio.to_thread(
                image_analyzer.analyze_qpf_from_image, pop6_url, sample_xy
            ) if pop6_url else None

            # Analyze daily rain
            daily_rain_data = await asyncio.to_thread(
                image_analyzer.analyze_qpf_from_image, daily_rain_url, sample_xy
            ) if daily_rain_url else None

            # Analyze nowcast
            nowcast_data = []
            if nowcast_base_url:
                base_url = nowcast_base_url.rsplit('_', 1)[0]
                nowcast_urls = [f"{base_url}_f{h:02d}h.gif" for h in range(1, 13)]
                for url in nowcast_urls:
                    nowcast_data.append(await asyncio.to_thread(image_analyzer.analyze_ncdr_rain_from_image, url, sample_xy))

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
                "qpf12_max_mm_per_hr": pop12_data.get("max") if pop12_data else None,
                "qpf12_min_mm_per_hr": pop12_data.get("min") if pop12_data else None,
                "qpf6_max_mm_per_hr": pop6_data.get("max") if pop6_data else None,
                "qpf6_min_mm_per_hr": pop6_data.get("min") if pop6_data else None,
                "daily_rain": daily_rain_data,
                "nowcast": nowcast_data,
                "aqi_level": aqi_level,
            }
        
        CACHED_IMAGE_METRICS.clear()
        CACHED_IMAGE_METRICS.update(image_metrics)
        
        print(f"Image analysis complete. Metrics cached for {len(image_metrics)} counties.")

    except Exception as e:
        print(f"Error analyzing images: {e}")

    if CACHED_CWA_TOWNSHIP_DATA:
        print("Scheduled job finished. CWA data has been cached.")
        CACHED_FINAL_JSON = json_generator.generate_json_output()
        print(f"Debug: township_weather map contains {len(township_weather)} entries.")
        
        if CACHED_WEATHER_DATA['township_weather']:
            print("Proceeding to generate and upload unified JSON file.")
            unified_data = json_generator.generate_unified_json()
        
            if unified_data:
                temp_dir = os.path.join(os.path.dirname(__file__), '..', 'temp')
                os.makedirs(temp_dir, exist_ok=True)
                local_file_path = os.path.join(temp_dir, "all_forecasts.txt")
                destination_blob_name = f"forecasts/all_forecasts_{datetime.datetime.now().strftime('%Y%m%d%H%M')}.txt"

                try:
                    with open(local_file_path, 'w', encoding='utf-8') as f:
                        json.dump(unified_data, f, ensure_ascii=False, indent=4)
                    print(f"Successfully saved unified data to {local_file_path}")

                    if os.getenv('FIREBASE_STORAGE_BUCKET'):
                        upload_url = firebase_uploader.upload_file_to_storage(local_file_path, destination_blob_name)
                        if upload_url:
                            print("Firebase upload successful.")
                        else:
                            print("Firebase upload failed.")
                    else:
                        print("Warning: FIREBASE_STORAGE_BUCKET env var not set. Skipping Firebase upload.")

                except Exception as e:
                    print(f"Error during file generation or upload: {e}")
                finally:
                    if os.path.exists(local_file_path):
                        os.remove(local_file_path)
                        print(f"Cleaned up temporary file: {local_file_path}")
            else:
                print("Unified JSON generation failed, skipping file creation and upload.")

        await check_and_send_notifications()
    else:
        print("Scheduled job finished. CWA data fetching failed.")

async def check_and_send_notifications():
    """
    Checks for notification conditions based on the cached CWA data.
    """
    print("Checking for notification conditions...")
    user_township = "臺北市中正區"
    user_device_token = "DEVICE_TOKEN_HERE" 

    forecast = calculation.get_forecast_for_township(user_township, CACHED_TOWNSHIP_MAP)

    if forecast and forecast.get("chance_of_rain_12h"):
        pop_value_str = forecast["chance_of_rain_12h"]
        if pop_value_str and pop_value_str.isdigit():
            pop_value = int(pop_value_str)
            if pop_value > 50:
                message = f"Weather Alert for {user_township}: Chance of rain is {pop_value}% in the next 12 hours."
                print(message)
                
                discord_sender.send_to_discord(message)

# Schedule the data fetching job to run twice daily at 06:00 and 12:00
scheduler.add_job(fetch_data_job, 'cron', hour='6,12', minute=20)

# --- Getter functions for API endpoints to access cached data ---
def get_cached_weather_data():
    return CACHED_WEATHER_DATA

def get_county_weather(county_name: str):
    return CACHED_WEATHER_DATA['county_weather'].get(county_name)

def get_township_weather(township_name: str):
    return CACHED_WEATHER_DATA['township_weather'].get(township_name)

def get_qpf_data(county_name: str):
    return CACHED_WEATHER_DATA['qpf_data'].get(county_name)

def get_aqi_data(county_name: str):
    return CACHED_WEATHER_DATA['aqi_data'].get(county_name)

def get_last_update_time():
    return CACHED_WEATHER_DATA['update_time']