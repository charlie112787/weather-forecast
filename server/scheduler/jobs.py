from apscheduler.schedulers.asyncio import AsyncIOScheduler
from server.core import data_fetcher, calculation, json_generator
from server.core import image_analyzer
from server.core import image_url_resolver
from server import config
from server.services import fcm_sender, discord_sender
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

def _iter_all_locations(records: object):
    # Yield all location dicts from various possible shapes
    if not isinstance(records, dict):
        return
    # Case 1: records.location is a list
    loc_list = records.get('location') if isinstance(records, dict) else None
    if isinstance(loc_list, list):
        for loc in loc_list:
            if isinstance(loc, dict):
                yield loc
    # Case 2: records.locations is a list of groups, each with group.location list
    groups = records.get('locations') if isinstance(records, dict) else None
    if isinstance(groups, list):
        for group in groups:
            if isinstance(group, dict):
                for loc in group.get('location', []) if isinstance(group.get('location'), list) else []:
                    if isinstance(loc, dict):
                        # Some structures have an extra nested 'location' list under each county
                        inner = loc.get('location')
                        if isinstance(inner, list):
                            for inner_loc in inner:
                                if isinstance(inner_loc, dict):
                                    yield inner_loc
                        else:
                            yield loc
    # Case 3: records.locations is a dict with key 'location' list
    if isinstance(groups, dict):
        inner_locs = groups.get('location')
        if isinstance(inner_locs, list):
            for loc in inner_locs:
                if isinstance(loc, dict):
                    inner = loc.get('location')
                    if isinstance(inner, list):
                        for inner_loc in inner:
                            if isinstance(inner_loc, dict):
                                yield inner_loc
                    else:
                        yield loc
    # Case 4: Capitalized structure: records['Locations']['Location'] list
    cap_groups = records.get('Locations')
    if isinstance(cap_groups, dict):
        cap_inner = cap_groups.get('Location')
        if isinstance(cap_inner, list):
            for loc in cap_inner:
                if isinstance(loc, dict):
                    inner = loc.get('location') or loc.get('Location')
                    if isinstance(inner, list):
                        for inner_loc in inner:
                            if isinstance(inner_loc, dict):
                                yield inner_loc
                    else:
                        yield loc
    if isinstance(cap_groups, list):
        for group in cap_groups:
            if isinstance(group, dict):
                # group keys example: 'DatasetDescription', 'LocationsName', 'Dataid', 'Location'
                cap_inner = group.get('Location')
                if isinstance(cap_inner, list):
                    for loc in cap_inner:
                        if isinstance(loc, dict):
                            inner = loc.get('location') or loc.get('Location')
                            if isinstance(inner, list):
                                for inner_loc in inner:
                                    if isinstance(inner_loc, dict):
                                        yield inner_loc
                            else:
                                yield loc

async def _fetch_weather_data(county_data=None):
    """Fetches both county and township level weather data."""
    if county_data is None:
        # 如果沒有提供縣市資料，則獲取它
        county_data = await asyncio.to_thread(data_fetcher.get_cwa_county_forecast_data)
    
    # 獲取所有縣市的鄉鎮級資料
    township_data_tasks = []
    for city in data_fetcher.CWA_TOWNSHIP_CODES.keys():
        township_data_tasks.append(
            asyncio.to_thread(data_fetcher.get_cwa_township_forecast_data, city)
        )
    
    # 並行獲取所有鄉鎮資料
    township_data_results = await asyncio.gather(*township_data_tasks)
    
    # 合併所有鄉鎮資料
    all_township_data = {
        'records': {
            'locations': []
        }
    }
    for data in township_data_results:
        if data and 'records' in data and 'locations' in data['records']:
            all_township_data['records']['locations'].extend(data['records']['locations'])
    
    # 處理縣市資料
    county_weather = {}
    if county_data and 'records' in county_data:
        for location in county_data['records'].get('location', []):
            county_name = location.get('locationName')
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
    if all_township_data and 'records' in all_township_data:
        for locations in all_township_data['records'].get('locations', []):
            for location in locations.get('location', []):
                township_name = location.get('locationName')
                if township_name:
                    # 從 locationName 取得縣市名稱和鄉鎮名稱
                    parts = township_name.split('區') if '區' in township_name else township_name.split('鎮') if '鎮' in township_name else township_name.split('市') if '市' in township_name else [township_name]
                    if len(parts) >= 2:
                        county_name = parts[0]
                        township_name = parts[1]
                        full_name = f"{county_name}{township_name}"
                    else:
                        full_name = township_name
                    weather_elements = {}
                    for element in location.get('weatherElement', []):
                        name = element.get('elementName')
                        if name and element.get('time'):
                            values = element['time'][0].get('elementValue', [])
                            if values:
                                weather_elements[name] = values[0].get('value')
                    
                    township_weather[full_name] = {
                        'pop6h': weather_elements.get('6小時降雨機率'),
                        'pop12h': weather_elements.get('12小時降雨機率')
                    }
    
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
    pop12_url = await asyncio.to_thread(
        image_url_resolver.resolve_latest_url,
        config.POP12_URL_PATTERNS
    )
    pop6_url = await asyncio.to_thread(
        image_url_resolver.resolve_latest_url,
        config.POP6_URL_PATTERNS
    )
    
    # 獲取降雨強度
    qpf_data = {}
    if pop12_url or pop6_url:
        for county_name, coords in config.IMAGE_SAMPLE_COORDS.items():
            qpf12 = await asyncio.to_thread(
                image_analyzer.analyze_qpf_from_image,
                pop12_url,
                coords
            ) if pop12_url else None
            
            qpf6 = await asyncio.to_thread(
                image_analyzer.analyze_qpf_from_image,
                pop6_url,
                coords
            ) if pop6_url else None
            
            qpf_data[county_name] = {
                'qpf12': qpf12,
                'qpf6': qpf6
            }
    
    # 獲取空氣品質數據
    aqi_url = await asyncio.to_thread(
        image_url_resolver.resolve_latest_url,
        config.AQI_URL_PATTERNS
    )
    
    aqi_data = {}
    if aqi_url:
        for county_name, coords in config.IMAGE_SAMPLE_COORDS.items():
            aqi = await asyncio.to_thread(
                image_analyzer.analyze_aqi_from_image,
                aqi_url,
                coords
            )
            if aqi:
                aqi_data[county_name] = aqi

    # Image-derived metrics
    try:
        if config.TESSERACT_CMD:
            image_analyzer.configure_tesseract_cmd(config.TESSERACT_CMD)
        # Resolve static or dynamic URLs for PoP12 / PoP6 (network I/O -> thread)
        pop12_resolved = await asyncio.to_thread(
            image_url_resolver.resolve_latest_url, config.POP12_URL_PATTERNS
        )
        pop6_resolved = await asyncio.to_thread(
            image_url_resolver.resolve_latest_url, config.POP6_URL_PATTERNS
        )
        pop12_url = (
            config.POP12_IMAGE_URL or pop12_resolved or config.RAIN_PROBABILITY_IMAGE_URL
        )
        pop6_url = (
            config.POP6_IMAGE_URL or pop6_resolved or config.RAIN_PROBABILITY_IMAGE_URL
        )

        # Backward-compatible single PoP (if both None later)
        single_pop_url = config.RAIN_PROBABILITY_IMAGE_URL

        pop12 = await asyncio.to_thread(
            image_analyzer.extract_rain_probability_from_image,
            pop12_url,
            (config.POP12_CROP_BOX or config.RAIN_PROBABILITY_CROP_BOX),
        ) if pop12_url else None
        pop6 = await asyncio.to_thread(
            image_analyzer.extract_rain_probability_from_image,
            pop6_url,
            (config.POP6_CROP_BOX or config.RAIN_PROBABILITY_CROP_BOX),
        ) if pop6_url else None

        pop_single = await asyncio.to_thread(
            image_analyzer.extract_rain_probability_from_image,
            single_pop_url,
            config.RAIN_PROBABILITY_CROP_BOX,
        ) if single_pop_url and pop12 is None and pop6 is None else None
        # Resolve AQI URL (static or dynamic)
        aqi_resolved = await asyncio.to_thread(
            image_url_resolver.resolve_latest_url, config.AQI_URL_PATTERNS
        )
        aqi_url = (config.AQI_IMAGE_URL or aqi_resolved)
        aqi = await asyncio.to_thread(
            image_analyzer.analyze_aqi_from_image,
            aqi_url,
            config.AQI_SAMPLE_BOX,
        ) if aqi_url else None

        # QPF per-county cache: compute for all configured counties
        qpf_cache_by_county = {}
        if pop12_url or pop6_url:
            for county, sample_xy in (config.IMAGE_SAMPLE_COORDS or {}).items():
                if not sample_xy:
                    continue
                q12 = await asyncio.to_thread(
                    image_analyzer.analyze_qpf_from_image, pop12_url, sample_xy
                ) if pop12_url else None
                q6 = await asyncio.to_thread(
                    image_analyzer.analyze_qpf_from_image, pop6_url, sample_xy
                ) if pop6_url else None
                qpf_cache_by_county[county] = {
                    "qpf12_mm_per_hr": q12,
                    "qpf6_mm_per_hr": q6,
                }
        CACHED_IMAGE_METRICS = {
            "rain_probability_percent": pop_single,
            "pop12_percent": pop12 if pop12 is not None else pop_single,
            "pop6_percent": pop6 if pop6 is not None else pop_single,
            "aqi_level": aqi,
            # Not county-specific here; per-county QPF exposed via getter below
            "qpf12_mm_per_hr": None,
            "qpf6_mm_per_hr": None,
        }
        # Store per-county QPF cache on module (simple global)
        global QPF_CACHE_BY_COUNTY
        QPF_CACHE_BY_COUNTY = qpf_cache_by_county
    except Exception as e:
        print(f"Error analyzing images: {e}")
    
    if CACHED_CWA_TOWNSHIP_DATA:
        # --- Rebuild township map ---
        new_township_map = {}
        try:
            records = CACHED_CWA_TOWNSHIP_DATA.get('records', {})
            locations = records.get('Locations', [])
            
            if isinstance(locations, list) and locations:
                # 獲取主要的位置組
                main_location = locations[0]
                if isinstance(main_location, dict):
                    # 取得所有縣市
                    counties = main_location.get('Location', [])
                    print(f"Found {len(counties)} counties/cities")
                    
                    for county in counties:
                        if isinstance(county, dict):
                            county_name = county.get('LocationName')
                            weather_elements = county.get('WeatherElement', [])
                            
                            print(f"Processing {county_name}")
                            
                            # 為每個縣市創建基本天氣資料結構
                            for element in weather_elements:
                                element_name = element.get('ElementName')
                                time_array = element.get('Time', [])
                                if time_array:
                                    first_time = time_array[0]
                                    element_values = first_time.get('ElementValue', [])
                                    if element_values:
                                        value = element_values[0].get('value')
                                        # 根據縣市名稱和行政區建立完整地名
                                        if county_name:
                                            full_name = county_name
                                            new_township_map[_normalize_name(full_name)] = county
            
            print(f"Building township map: found {len(new_township_map)} townships")
            CACHED_TOWNSHIP_MAP = new_township_map
            
            if not CACHED_TOWNSHIP_MAP:
                print("Warning: Township map was built but is empty. Check CWA data structure again.")
            else:
                print(f"Successfully built township map with {len(CACHED_TOWNSHIP_MAP)} entries.")
        except (KeyError, IndexError, TypeError) as e:
            print(f"Error building township map due to unexpected data structure: {e}")

        print("Scheduled job finished. CWA data has been cached.")
        # After fetching data, generate the final JSON output
        global CACHED_FINAL_JSON
        CACHED_FINAL_JSON = json_generator.generate_json_output()
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

# Per-county QPF getters
QPF_CACHE_BY_COUNTY = {}
def get_qpf_for_county(county_name: str):
    return QPF_CACHE_BY_COUNTY.get(county_name)