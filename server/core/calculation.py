import json

def _normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    # Normalize common variants and whitespace
    return name.replace("台", "臺").replace(" ", "").strip()


def get_forecast_for_township(township_name: str, township_map: dict):
    """
    Extracts and processes CWA forecast data for a specific township using an efficient lookup map.

    Args:
        township_name: The full name of the township (e.g., "臺北市中正區").
        township_map: A pre-processed dictionary mapping normalized township names to their data.

    Returns:
        A dictionary containing the processed forecast, or None if not found.
    """
    if not township_map:
        print("Error: Township map is not available or empty.")
        return None

    normalized_name = _normalize_name(township_name)
    cwa_location_data = township_map.get(normalized_name)

    if not cwa_location_data:
        print(f"Error: Township '{township_name}' not found in the map. Normalized name: '{normalized_name}'")
        return None

    # 2) Extract weather elements
    weather_elements = {}
    for element in cwa_location_data.get('WeatherElement', []):
        element_name = element.get('ElementName')
        element_value = "N/A"
        time_arr = element.get('Time') or []
        if time_arr:
            first = time_arr[0]
            if isinstance(first, dict) and 'ElementValue' in first and first['ElementValue']:
                ev = first['ElementValue'][0]
                if isinstance(ev, dict):
                    if element_name == "天氣現象":
                        element_value = ev.get("Weather")
                    elif element_name == "降雨機率":
                        element_value = ev.get("ProbabilityOfPrecipitation")
                    elif element_name == "溫度":
                        element_value = ev.get("Temperature")

        if element_name:
            weather_elements[element_name] = element_value

    # 3) Build response
    return {
        "township": township_name,
        "cwa_forecast": {
            "temperature": weather_elements.get("溫度"),
            "chance_of_rain_12h": weather_elements.get("降雨機率"),
            "weather_description": weather_elements.get("天氣現象"),
        },
    }


def get_forecast_for_township_from_records(township_name: str, all_cwa_data: dict):
    """
    Fallback: Walk full CWA records to locate township and extract elements.
    """
    if not all_cwa_data or 'records' not in all_cwa_data:
        return None
    target = None
    records = all_cwa_data['records']
    # Traverse likely shapes
    groups = records.get('Locations')
    if isinstance(groups, list):
        for grp in groups:
            if not isinstance(grp, dict):
                continue
            counties = grp.get('Location')
            if isinstance(counties, list):
                for county in counties:
                    if not isinstance(county, dict):
                        continue
                    # Town list under county
                    towns = county.get('location') or county.get('Location')
                    if isinstance(towns, list):
                        for town in towns:
                            nm = town.get('locationName') or town.get('LocationName')
                            if _normalize_name(nm) == _normalize_name(township_name):
                                target = town
                                break
                        if target:
                            break
                if target:
                    break
    if target is None:
        # Last resort: scan any locations directly
        locs = records.get('location')
        if isinstance(locs, list):
            for loc in locs:
                nm = loc.get('locationName') or loc.get('LocationName') if isinstance(loc, dict) else None
                if _normalize_name(nm) == _normalize_name(township_name):
                    target = loc
                    break
    if target is None:
        return None
    weather_elements = {}
    for element in target.get('WeatherElement', []):
        element_name = element.get('ElementName')
        element_value = "N/A"
        time_arr = element.get('Time') or []
        if time_arr:
            first = time_arr[0]
            if isinstance(first, dict) and 'ElementValue' in first and first['ElementValue']:
                ev = first['ElementValue'][0]
                if isinstance(ev, dict):
                    if element_name == "天氣現象":
                        element_value = ev.get("Weather")
                    elif element_name == "降雨機率":
                        element_value = ev.get("ProbabilityOfPrecipitation")
                    elif element_name == "溫度":
                        element_value = ev.get("Temperature")

        if element_name:
            weather_elements[element_name] = element_value
    return {
        "township": township_name,
        "cwa_forecast": {
            "temperature": weather_elements.get("溫度"),
            "chance_of_rain_12h": weather_elements.get("降雨機率"),
            "weather_description": weather_elements.get("天氣現象"),
        },
    }
