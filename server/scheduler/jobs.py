from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ..core import data_fetcher, calculation
from ..services import fcm_sender
from PIL import Image

scheduler = AsyncIOScheduler()

# --- Data Cache ---
CACHED_CWA_DATA = None
CACHED_NCDR_IMAGE = None
# --- End of Cache ---

async def fetch_data_job():
    """
    Scheduled job to fetch and cache the raw data from all sources.
    """
    print("Running scheduled job: fetch_data_job")
    global CACHED_CWA_DATA, CACHED_NCDR_IMAGE

    CACHED_CWA_DATA = data_fetcher.get_cwa_township_forecast_data()
    CACHED_NCDR_IMAGE = data_fetcher.fetch_and_cache_ncdr_image()
    
    if isinstance(CACHED_NCDR_IMAGE, dict) and "message" in CACHED_NCDR_IMAGE:
        print(f"Warning: NCDR image fetch failed. Using last successful image or None. Error: {CACHED_NCDR_IMAGE['message']}")
    elif isinstance(CACHED_NCDR_IMAGE, Image.Image):
        print("Scheduled job finished. Data has been cached.")
    else:
        print("Scheduled job finished. NCDR Image not available.")

async def check_and_send_notifications():
    """
    Placeholder function to demonstrate notification logic.
    """
    print("Checking for notification conditions...")
    user_township = "臺北市中正區"
    user_device_token = "DEVICE_TOKEN_HERE"

    forecast = calculation.get_forecast_for_township(user_township, CACHED_CWA_DATA, CACHED_NCDR_IMAGE)

    if forecast and forecast["cwa_forecast"]["chance_of_rain_12h"]:
        pop_value = int(forecast["cwa_forecast"]["chance_of_rain_12h"]) if forecast["cwa_forecast"]["chance_of_rain_12h"].isdigit() else 0
        if pop_value > 50:
            max_rain = forecast["ncdr_forecast"].get("max_rainfall_mm_in_radius", "N/A")
            print(f"Condition met for {user_township}: Chance of rain is {pop_value}%, Max local rain: {max_rain}mm")
            # fcm_sender.send_notification(
            #      title=f"{user_township} Weather Alert",
            #      body=f"High chance of rain ({pop_value}%) in the next 12 hours. Max local rainfall: {max_rain}mm",
            #      token=user_device_token
            # )

scheduler.add_job(fetch_data_job, 'interval', hours=1)

def get_cached_cwa_data():
    return CACHED_CWA_DATA

def get_cached_ncdr_image():
    return CACHED_NCDR_IMAGE
