from apscheduler.schedulers.asyncio import AsyncIOScheduler
from server.core import data_fetcher, calculation
from server.core import image_analyzer
from server.core import image_url_resolver
from server import config
from server.services import fcm_sender, discord_sender
import asyncio

scheduler = AsyncIOScheduler()

# --- Data Cache ---
CACHED_CWA_TOWNSHIP_DATA = None
CACHED_CWA_COUNTY_DATA = None
CACHED_IMAGE_METRICS = {
    "rain_probability_percent": None,
    "pop12_percent": None,
    "pop6_percent": None,
    "aqi_level": None,
    "qpf12_mm_per_hr": None,
    "qpf6_mm_per_hr": None,
}
# --- End of Cache ---

async def fetch_data_job():
    """
    Scheduled job to fetch and cache CWA data.
    """
    print("Running scheduled job: fetch_data_job")
    global CACHED_CWA_TOWNSHIP_DATA, CACHED_CWA_COUNTY_DATA, CACHED_IMAGE_METRICS

    CACHED_CWA_TOWNSHIP_DATA = await asyncio.to_thread(
        data_fetcher.get_cwa_township_forecast_data
    )
    CACHED_CWA_COUNTY_DATA = await asyncio.to_thread(
        data_fetcher.get_cwa_county_forecast_data
    )

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
        try:
            # diagnostics: count available township locations
            records = CACHED_CWA_TOWNSHIP_DATA.get('records', {}) if isinstance(CACHED_CWA_TOWNSHIP_DATA, dict) else {}
            print(f"records type: {type(records).__name__}")
            if isinstance(records, dict):
                print(f"records keys: {list(records.keys())[:10]}")
                locs_cap = records.get('Locations')
                if isinstance(locs_cap, dict):
                    print(f"records['Locations'] keys: {list(locs_cap.keys())[:10]}")
                if isinstance(locs_cap, list) and locs_cap:
                    first_keys = list(locs_cap[0].keys()) if isinstance(locs_cap[0], dict) else []
                    print(f"records['Locations'][0] keys: {first_keys}")
            def _iter_locations(rec):
                if isinstance(rec, dict):
                    locs = rec.get('location')
                    if isinstance(locs, list):
                        for loc in locs:
                            yield loc
                    groups = rec.get('locations')
                    if isinstance(groups, list):
                        for g in groups:
                            if isinstance(g, dict):
                                inner = g.get('location')
                                if isinstance(inner, list):
                                    for loc in inner:
                                        yield loc
                    if isinstance(groups, dict):
                        inner = groups.get('location')
                        if isinstance(inner, list):
                            for loc in inner:
                                yield loc
                    # Capitalized variants
                    caps = rec.get('Locations')
                    if isinstance(caps, list):
                        for g in caps:
                            if isinstance(g, dict):
                                inner = g.get('Location')
                                if isinstance(inner, list):
                                    for loc in inner:
                                        yield loc
                    if isinstance(caps, dict):
                        inner = caps.get('Location')
                        if isinstance(inner, list):
                            for loc in inner:
                                yield loc
            sample = []
            count = 0
            for loc in _iter_locations(records):
                count += 1
                if len(sample) < 10 and isinstance(loc, dict):
                    name = loc.get('locationName') or loc.get('LocationName')
                    if name:
                        sample.append(name)
            print(f"Township records discovered: {count}")
            print(f"First township names: {sample}")
        except Exception as _e:
            pass
        print("Scheduled job finished. CWA data has been cached.")
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

    forecast = calculation.get_forecast_for_township(user_township, CACHED_CWA_TOWNSHIP_DATA)

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
def get_cached_cwa_township_data():
    return CACHED_CWA_TOWNSHIP_DATA

def get_cached_cwa_county_data():
    return CACHED_CWA_COUNTY_DATA

def get_cached_image_metrics():
    return CACHED_IMAGE_METRICS

# Per-county QPF getters
QPF_CACHE_BY_COUNTY = {}
def get_qpf_for_county(county_name: str):
    return QPF_CACHE_BY_COUNTY.get(county_name)