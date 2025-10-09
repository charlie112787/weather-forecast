import datetime
from scheduler import jobs
from . import codes
import json

def generate_unified_json():
    """
    Generates a single, unified JSON object containing all forecast data for every township in Taiwan.
    This function is the single source of truth for creating the final data package.
    """
    print("Starting generation of unified JSON for all townships...")
    
    # 1. Get all cached data sources
    update_time = datetime.datetime.now().isoformat()
    cwa_county_data = jobs.get_cached_weather_data().get('county_weather')
    cwa_township_data = jobs.get_cached_weather_data().get('township_weather')
    image_metrics = jobs.CACHED_IMAGE_METRICS

    if not cwa_county_data or not cwa_township_data:
        print("Error: CWA data caches are not available. Cannot generate unified JSON.")
        return None

    final_data = {
        "update_time": update_time,
        "towns": {}
    }

    # 2. Iterate through every known township
    for township_full_name, township_code in codes.TOWNSHIP_NAME_TO_CODE.items():
        
        # 3. For each township, find its data from all sources
        county_name = codes.resolve_county_from_township_name(township_full_name)
        
        # Normalize names for cache lookups
        normalized_town_name = codes.normalize_name(township_full_name)
        normalized_county_name = codes.normalize_name(county_name)

        # Get data from CWA caches
        town_cwa = cwa_township_data.get(normalized_town_name)
        county_cwa = cwa_county_data.get(normalized_county_name)

        # Get data from image analysis cache
        county_image_metrics = image_metrics.get(county_name) or {}

        # --- Start assembling the data for one township ---
        
        # From county-level CWA data
        temperature = county_cwa.get('temperature') if county_cwa else None
        
        # From township-level CWA data
        pop6h = None
        pop12h = None
        weather_description = None
        if town_cwa and town_cwa.get('weatherElement'):
            for element in town_cwa['weatherElement']:
                element_name = element.get('elementName')
                time_data = element.get('time', [{}])[0]
                
                if element_name == '天氣現象':
                    weather_description = time_data.get('elementValue', [{}])[0].get('value')
                # The CWA township data provides PoP in 3-hour intervals.
                elif element_name == '3小時降雨機率':
                    pop_value = time_data.get('elementValue', [{}])[0].get('value')
                    # Use the first 3-hour value for both 6h and 12h for now.
                    if pop6h is None: # Only assign once
                        pop6h = pop_value
                    if pop12h is None: # Only assign once
                        pop12h = pop_value

        # Assemble all data into a single object
        township_data_object = {
            "township_name": township_full_name,
            "county_name": county_name,
            "temperature": temperature,
            "weather_description": weather_description,
            "pop6h": pop6h,
            "pop12h": pop12h,
            "aqi_level": county_image_metrics.get("aqi_level"),
            "cwa_qpf_6h_min": county_image_metrics.get("qpf6_min_mm_per_hr"),
            "cwa_qpf_6h_max": county_image_metrics.get("qpf6_max_mm_per_hr"),
            "cwa_qpf_12h_min": county_image_metrics.get("qpf12_min_mm_per_hr"),
            "cwa_qpf_12h_max": county_image_metrics.get("qpf12_max_mm_per_hr"),
            "ncdr_daily_rain_min": (county_image_metrics.get("ncdr_daily_rain") or {}).get("min"),
            "ncdr_daily_rain_max": (county_image_metrics.get("ncdr_daily_rain") or {}).get("max"),
            "ncdr_nowcast": county_image_metrics.get("ncdr_nowcast"),
        }
        
        final_data["towns"][township_code] = township_data_object

    print(f"Successfully generated unified JSON for {len(final_data['towns'])} townships.")
    return final_data

# This function is kept for compatibility with older parts of the code if needed,
# but generate_unified_json is the new primary function.
def generate_json_output():
    return generate_unified_json()