import requests
from .. import config
from datetime import datetime, timedelta
from PIL import Image
import io
import math

# --- NCDR Color to Rainfall Mapping ---
COLOR_TO_RAINFALL_MAPPING = {
    (230, 255, 230): 0.1,
    (170, 255, 170): 1.0,
    (100, 255, 100): 2.0,
    (255, 255, 0): 5.0,
    (255, 200, 0): 10.0,
    (255, 150, 0): 15.0,
    (255, 0, 0): 25.0,
    (255, 0, 255): 40.0,
    (150, 0, 255): 60.0,
    (0, 0, 255): 80.0,
    (0, 0, 150): 100.0,
    (0, 0, 50): 130.0,
    (100, 100, 100): 200.0,
}

CWA_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/"

def get_cwa_township_forecast_data():
    """
    Fetches 36-hour weather forecast data for all townships in Taiwan from the CWA API.
    """
    dataset_id = "F-D0047-091"
    url = f"{CWA_API_URL}{dataset_id}"
    params = {"Authorization": config.CWA_API_KEY}
    try:
        print("Fetching CWA township forecast data...")
        response = requests.get(url, params=params)
        response.raise_for_status()
        print("Successfully fetched CWA data.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching CWA township data: {e}")
        return None

def get_ncdr_image_url():
    """Dynamically constructs the most recent valid URL for a CWA product image."""
    now_utc = datetime.utcnow()
    issue_hours_utc = [2, 8, 14, 20]
    
    latest_issue_hour = -1
    for hour in reversed(issue_hours_utc):
        if now_utc.hour >= hour:
            latest_issue_hour = hour
            break
    
    issue_date = now_utc
    if latest_issue_hour == -1:
        issue_date -= timedelta(days=1)
        latest_issue_hour = issue_hours_utc[-1]

    issue_time = issue_date.replace(hour=latest_issue_hour, minute=0, second=0, microsecond=0)
    issue_time_str = issue_time.strftime('%Y%m%d%H')
    
    base_url = f"https://www.cwa.gov.tw/Data/NWP/P_C_NWRF_6h_QPF_{issue_time_str}_T06.png"
    return base_url

def map_color_to_value(rgb_tuple):
    """
    Finds the closest color in COLOR_TO_RAINFALL_MAPPING using Euclidean distance
    and returns its corresponding rainfall value.
    """
    min_distance = float('inf')
    rainfall_value = 0.0
    for color, value in COLOR_TO_RAINFALL_MAPPING.items():
        distance_sq = sum([(color[i] - rgb_tuple[i]) ** 2 for i in range(3)])
        if distance_sq < min_distance:
            min_distance = distance_sq
            rainfall_value = value
    return rainfall_value

def fetch_and_cache_ncdr_image():
    """
    Downloads NCDR forecast images and returns the PIL Image object.
    """
    print("Running NCDR image fetch job...")
    ncdr_image_url = get_ncdr_image_url()
    try:
        print(f"Downloading NCDR image from: {ncdr_image_url}")
        response = requests.get(ncdr_image_url)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content)).convert("RGB")
        print("Successfully fetched NCDR image.")
        return img
    except requests.exceptions.HTTPError as e:
        print(f"Error downloading NCDR image (HTTP Error): {e}. URL used: {ncdr_image_url}")
        return {"message": "NCDR image download failed due to HTTP error (e.g., 404 Not Found)"}
    except Exception as e:
        print(f"Error processing NCDR image: {e}")
        return {"message": "NCDR image processing failed"}

def get_max_rainfall_in_radius(img: Image, center_x: int, center_y: int, radius: int) -> float:
    """
    Scans a circular radius on the NCDR image to find the maximum rainfall value.
    """
    if not isinstance(img, Image.Image):
        print("Error: NCDR image cache is not a valid PIL Image object.")
        return 0.0
        
    max_rainfall = 0.0
    img_width, img_height = img.size
    
    for x in range(center_x - radius, center_x + radius + 1):
        for y in range(center_y - radius, center_y + radius + 1):
            if 0 <= x < img_width and 0 <= y < img_height:
                if math.sqrt((x - center_x)**2 + (y - center_y)**2) <= radius:
                    try:
                        rgb_tuple = img.getpixel((x, y))
                        rainfall_value = map_color_to_value(rgb_tuple)
                        if rainfall_value > max_rainfall:
                            max_rainfall = rainfall_value
                    except Exception as e:
                        pass 
    return max_rainfall
