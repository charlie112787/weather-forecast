from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ..core import data_fetcher, calculation
from ..services import fcm_sender

scheduler = AsyncIOScheduler()

# --- Data Cache ---
# These global variables will act as a simple in-memory cache for the fetched data.
CACHED_CWA_DATA = None
CACHED_NCDR_GRID = None
# --- End of Cache ---

async def fetch_data_job():
    """
    Scheduled job to fetch and cache the raw data from all sources.
    """
    print("Running scheduled job: fetch_data_job")
    global CACHED_CWA_DATA, CACHED_NCDR_GRID

    # 1. Fetch CWA data for all townships
    CACHED_CWA_DATA = data_fetcher.get_cwa_township_forecast_data()

    # 2. Fetch and pre-compute NCDR grid data from images
    CACHED_NCDR_GRID = data_fetcher.precompute_ncdr_grid_data()
    
    print("Scheduled job finished. Data has been cached.")
    # In a real application, you would trigger notifications here based on the new data.
    # For example, loop through subscribed users and check their locations.
    # await check_and_send_notifications()

async def check_and_send_notifications():
    """
    Placeholder function to demonstrate notification logic.
    In a real app, this would read user preferences from a database.
    """
    print("Checking for notification conditions...")
    # Example: A user is subscribed to notifications for "臺北市中正區"
    user_township = "臺北市中正區"
    user_device_token = "DEVICE_TOKEN_HERE" # This would come from your database

    forecast = calculation.get_forecast_for_township(user_township, CACHED_CWA_DATA, CACHED_NCDR_GRID)

    if forecast and forecast["cwa_forecast"]["chance_of_rain_12h"]:
        pop_value = int(forecast["cwa_forecast"]["chance_of_rain_12h"])
        if pop_value > 50: # Condition: chance of rain > 50%
            print(f"Condition met for {user_township}: Chance of rain is {pop_value}%")
            # fcm_sender.send_notification(
            #     title=f"{user_township} Weather Alert",
            #     body=f"High chance of rain ({pop_value}%) in the next 12 hours.",
            #     token=user_device_token
            # )

# Schedule the data fetching job to run periodically (e.g., every hour)
scheduler.add_job(fetch_data_job, 'interval', hours=1)

# --- Getter functions for API endpoints to access cached data ---
def get_cached_cwa_data():
    return CACHED_CWA_DATA

def get_cached_ncdr_grid():
    return CACHED_NCDR_GRID