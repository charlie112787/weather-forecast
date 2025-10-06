import requests
from .. import config
from datetime import datetime
from PIL import Image
import io

# --- NCDR Color to Rainfall Mapping ---
# This map translates RGB colors to cumulative rainfall in millimeters.
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
    """Dynamically constructs the URL for a CWA product image.
    
    This assumes the target is the latest 6-hour QPF map from the NWRF model.
    URL format may need adjustments based on actual NCDR/CWA system rules.
    """
    now = datetime.now()
    issue_time_str = now.strftime('%Y%m%d%H')
    base_url = "https://www.cwa.gov.tw/Data/NWP/P_C_NWRF_6h_QPF_{time}_T06.png"
    return base_url.replace('{time}', issue_time_str)

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

def precompute_ncdr_grid_data():
    """
    Downloads NCDR forecast images, processes them into a 10x7 grid of rainfall data.
    """
    print("Running NCDR grid precomputation...")
    
    ncdr_image_url = get_ncdr_image_url()
    top_left_xy = (120, 100)
    bottom_right_xy = (900, 1050)
    grid_width = 7
    grid_height = 10
    
    try:
        print(f"Downloading NCDR image from: {ncdr_image_url}")
        response = requests.get(ncdr_image_url)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content)).convert("RGB")
        
        ncdr_grid = {}
        total_width = bottom_right_xy[0] - top_left_xy[0]
        total_height = bottom_right_xy[1] - top_left_xy[1]
        cell_width = total_width / grid_width
        cell_height = total_height / grid_height
        
        print("Calculating grid data from image...")
        for row in range(grid_height):
            for col in range(grid_width):
                center_x = int(top_left_xy[0] + (col + 0.5) * cell_width)
                center_y = int(top_left_xy[1] + (row + 0.5) * cell_height)
                rgb_tuple = img.getpixel((center_x, center_y))
                rainfall_value = map_color_to_value(rgb_tuple)
                
                grid_id = f"R{row+1}_C{col+1}"
                ncdr_grid[grid_id] = {"rainfall_mm": rainfall_value}

        print(f"Successfully computed a {grid_height}x{grid_width} NCDR grid.")
        return ncdr_grid
        
    except requests.exceptions.HTTPError as e:
        print(f"Error downloading NCDR image (HTTP Error): {e}. URL used: {ncdr_image_url}")
        return {"message": "NCDR image download failed due to HTTP error (e.g., 404 Not Found)"}
    except Exception as e:
        print(f"Error processing NCDR image: {e}")
        return {"message": "NCDR image processing failed"}