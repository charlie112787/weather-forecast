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

    print(f"Debug: county_data keys: {county_data.keys()}")
    records = county_data.get('records', {})
    locations = records.get('location', [])
    print(f"Debug: Found {len(locations)} locations in county_data.")

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
                    print(f"[CWA] Township fetched: {full_name} -> normalized: {normalized_name}")
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
                print(f"[CWA] County parsed: {county_name} elements={list(weather_elements.keys())}")
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
        county_data = await asyncio.to_thread(data_fetcher.get_cwa_county_forecast_data)
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
                'update_time': datetime.datetime.now().isoformat()
            })
    except Exception as e:
        print(f"Error in fetch_data_job while fetching weather data: {e}")
        return
    
    try:
        if config.TESSERACT_CMD:
            image_analyzer.configure_tesseract_cmd(config.TESSERACT_CMD)

        pop12_url = await asyncio.to_thread(image_url_resolver.resolve_latest_url, config.POP12_URL_PATTERNS)
        pop6_url = await asyncio.to_thread(image_url_resolver.resolve_latest_url, config.POP6_URL_PATTERNS)
        daily_rain_url = image_url_resolver.resolve_ncdr_daily_rain_url()
        nowcast_base_url = await asyncio.to_thread(image_url_resolver.resolve_latest_url, config.NCDR_NOWCAST_URL_PATTERN)
        aqi_url = await asyncio.to_thread(image_url_resolver.resolve_latest_url, config.AQI_URL_PATTERNS)

        image_metrics = {}

        # 使用三錨點 + TOWNSHIP_COORDS 自動推算座標；如未提供則略過影像分析
        township_coords = getattr(config, 'TOWNSHIP_COORDS', None)
        if not township_coords:
            print("Warning: TOWNSHIP_COORDS not configured in config.py. Skipping image analysis.")
            return

        # 生成兩種尺寸的鄉鎮像素座標；預設優先使用 450x810
        pixel_maps = image_analyzer.build_pixel_maps_from_township_coords(township_coords)
        px_450_810 = pixel_maps.get("450x810", {})
        px_315_642 = pixel_maps.get("315x642", {})
        print(f"[IMG] Built pixel map: 450x810 towns={len(px_450_810)}")
        print(f"[IMG] Built pixel map: 315x642 towns={len(px_315_642)}")

        # 選擇使用的像素地圖：優先用每日雨量圖尺寸；若不匹配則嘗試 POP12；若仍不匹配則做線性縮放
        active_px_map = px_450_810
        active_base_size = (450, 810)
        try:
            test_url = daily_rain_url or pop12_url or pop6_url
            if test_url:
                img = await asyncio.to_thread(image_analyzer._download_image, test_url)  # type: ignore[attr-defined]
                w, h = img.width, img.height
                print(f"[IMG] Detected image size: {w}x{h}")
                if (w, h) == (450, 810):
                    active_px_map = px_450_810
                    active_base_size = (450, 810)
                elif (w, h) == (315, 642):
                    active_px_map = px_315_642
                    active_base_size = (315, 642)
                else:
                    # 做簡單等比縮放（以 450x810 為基準）
                    sx = w / 450.0
                    sy = h / 810.0
                    print(f"[IMG] Scaling pixel map from 450x810 by ({sx:.3f}, {sy:.3f})")
                    scaled = {}
                    for name, (x, y) in px_450_810.items():
                        scaled[name] = (int(round(x * sx)), int(round(y * sy)))
                    active_px_map = scaled
                    active_base_size = (w, h)
        except Exception as e:
            print(f"[IMG] Image size detection failed, fallback to 450x810 map: {e}")

        # 依縣市聚合：取該縣市所有鄉鎮的 min/max 匯總
        from core import codes as _codes
        counties = list(_codes.COUNTY_NAME_TO_CODE.keys())

        for county in counties:
            # 該縣市的所有鄉鎮名（完整名稱）
            town_names = [t for t in _codes.TOWNSHIP_NAME_TO_CODE.keys() if t.startswith(county)]
            # 轉成像素座標，若缺少則略過
            town_pixels = [active_px_map.get(t) for t in town_names if active_px_map.get(t)]
            if not town_pixels:
                print(f"[IMG] Skip county (no pixels): {county}")
                image_metrics[county] = {
                    "qpf12_max_mm_per_hr": None,
                    "qpf12_min_mm_per_hr": None,
                    "qpf6_max_mm_per_hr": None,
                    "qpf6_min_mm_per_hr": None,
                    "daily_rain": None,
                    "nowcast": [],
                    "aqi_level": None,
                }
                continue

            # POP12/POP6（CWA 圖）：聚合鄉鎮 min/max
            print(f"[IMG] County start: {county} towns_with_pixels={len(town_pixels)}")
            pop12_min = None; pop12_max = None
            if pop12_url:
                print(f"[IMG] {county} POP12 analyzing @ {pop12_url}")
                # Debug: 存圖與位置
                if getattr(config, 'DEBUG_SAVE_SAMPLES', False):
                    from server import config as _cfg
                    if getattr(_cfg, 'DEBUG_SAVE_PER_TOWNSHIP', False):
                        for tname, xy in zip(town_names, town_pixels):
                            out_path = os.path.join(_cfg.DEBUG_SAVE_DIR, f"{tname}_POP12.png")
                            await asyncio.to_thread(image_analyzer.save_overlay, pop12_url, [xy], 12, out_path)
                    else:
                        out_path = os.path.join(_cfg.DEBUG_SAVE_DIR, f"{county}_POP12.png")
                        await asyncio.to_thread(image_analyzer.save_overlay, pop12_url, town_pixels, 12, out_path)
                for xy in town_pixels:
                    r = await asyncio.to_thread(image_analyzer.analyze_qpf_from_image, pop12_url, xy)
                    if r:
                        pop12_min = r["min"] if pop12_min is None else min(pop12_min, r["min"])
                        pop12_max = r["max"] if pop12_max is None else max(pop12_max, r["max"])

            pop6_min = None; pop6_max = None
            if pop6_url:
                print(f"[IMG] {county} POP6 analyzing @ {pop6_url}")
                if getattr(config, 'DEBUG_SAVE_SAMPLES', False):
                    from server import config as _cfg
                    if getattr(_cfg, 'DEBUG_SAVE_PER_TOWNSHIP', False):
                        for tname, xy in zip(town_names, town_pixels):
                            out_path = os.path.join(_cfg.DEBUG_SAVE_DIR, f"{tname}_POP6.png")
                            await asyncio.to_thread(image_analyzer.save_overlay, pop6_url, [xy], 12, out_path)
                    else:
                        out_path = os.path.join(_cfg.DEBUG_SAVE_DIR, f"{county}_POP6.png")
                        await asyncio.to_thread(image_analyzer.save_overlay, pop6_url, town_pixels, 12, out_path)
                for xy in town_pixels:
                    r = await asyncio.to_thread(image_analyzer.analyze_qpf_from_image, pop6_url, xy)
                    if r:
                        pop6_min = r["min"] if pop6_min is None else min(pop6_min, r["min"])
                        pop6_max = r["max"] if pop6_max is None else max(pop6_max, r["max"])

            # 每日單張（NCDR）：聚合鄉鎮 min/max
            daily_rain_data = None
            if daily_rain_url:
                print(f"[IMG] {county} Daily rain analyzing @ {daily_rain_url}")
                
                # --- MODIFIED: Unconditionally save overlay image ---
                output_dir = "analyzed_images"
                out_path = os.path.join(output_dir, f"{county}_daily_analyzed.png")
                print(f"[IMG] Saving overlay for {county} to {out_path}")
                await asyncio.to_thread(image_analyzer.save_overlay, daily_rain_url, town_pixels, 12, out_path)
                # --- END MODIFICATION ---

                daily_min = None; daily_max = None
                for xy in town_pixels:
                    r = await asyncio.to_thread(image_analyzer.analyze_ncdr_rain_from_image, daily_rain_url, xy)
                    if r:
                        daily_min = r["min"] if daily_min is None else min(daily_min, r["min"])
                        daily_max = r["max"] if daily_max is None else max(daily_max, r["max"])
                if daily_min is not None and daily_max is not None:
                    daily_rain_data = {"min": daily_min, "max": daily_max}

            # 12 張 Nowcast：對每張做一次聚合
            nowcast_data = []
            if nowcast_base_url:
                base_url = nowcast_base_url.rsplit('_', 1)[0]
                nowcast_urls = [f"{base_url}_f{h:02d}h.gif" for h in range(1, 13)]
                print(f"[IMG] {county} Nowcast analyzing ({len(nowcast_urls)} frames) base={base_url}")
                if getattr(config, 'DEBUG_SAVE_SAMPLES', False) and nowcast_urls:
                    # --- MODIFIED: Use the correct pixel map for nowcast images (assumed to be 315x642) and fix looping bug ---
                    nowcast_px_map = px_315_642
                    nowcast_town_pixels = [nowcast_px_map.get(t) for t in town_names if nowcast_px_map.get(t)]
                    town_name_to_pixel = {name: nowcast_px_map.get(name) for name in town_names}

                    from server import config as _cfg
                    if getattr(_cfg, 'DEBUG_SAVE_PER_TOWNSHIP', False):
                        # Save samples for the first two nowcast frames
                        for idx in [0, 1]:
                            url = nowcast_urls[idx]
                            for tname in town_names:
                                xy = town_name_to_pixel.get(tname)
                                if xy:
                                    out_path = os.path.join(_cfg.DEBUG_SAVE_DIR, f"{tname}_NOWCAST_f{idx+1:02d}.png")
                                    await asyncio.to_thread(image_analyzer.save_overlay, url, [xy], 12, out_path)
                    else:
                        out_path = os.path.join(_cfg.DEBUG_SAVE_DIR, f"{county}_NOWCAST_f01.png")
                        await asyncio.to_thread(image_analyzer.save_overlay, nowcast_urls[0], nowcast_town_pixels, 12, out_path)
                    # --- END MODIFICATION ---
                for url in nowcast_urls:
                    frame_min = None; frame_max = None
                    for xy in town_pixels:
                        r = await asyncio.to_thread(image_analyzer.analyze_ncdr_rain_from_image, url, xy)
                        if r:
                            frame_min = r["min"] if frame_min is None else min(frame_min, r["min"])
                            frame_max = r["max"] if frame_max is None else max(frame_max, r["max"])
                    if frame_min is None or frame_max is None:
                        nowcast_data.append({"min": 0.0, "max": 0.0})
                    else:
                        nowcast_data.append({"min": frame_min, "max": frame_max})

            # AQI 仍以縣市代表點取色（簡化）。如需同樣聚合可以改成所有鄉鎮再聚合
            aqi_level = None
            if aqi_url and town_pixels:
                # 取第一個像素點為代表
                x, y = town_pixels[0]
                box_size = 10
                sample_box = (x - box_size // 2, y - box_size // 2, x + box_size // 2, y + box_size // 2)
                aqi_level = await asyncio.to_thread(image_analyzer.analyze_aqi_from_image, aqi_url, sample_box)

            image_metrics[county] = {
                "qpf12_max_mm_per_hr": pop12_max,
                "qpf12_min_mm_per_hr": pop12_min,
                "qpf6_max_mm_per_hr": pop6_max,
                "qpf6_min_mm_per_hr": pop6_min,
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
        print(f"Debug: township_weather map contains {len(CACHED_WEATHER_DATA.get('township_weather') or {})} entries.")
        
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

# Trigger reload to regenerate sample images.
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