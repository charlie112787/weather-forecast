def _normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    # Normalize common variants and whitespace
    return name.replace("台", "臺").replace(" ", "").strip()


def _is_location_match(input_name: str, candidate_name: str) -> bool:
    a = _normalize_name(input_name)
    b = _normalize_name(candidate_name)
    if not a or not b:
        return False
    # Exact match only
    return a == b


def _iter_all_locations(records: object):
    # Yield all location dicts from various possible shapes
    if not isinstance(records, dict):
        return

    locations = records.get('Locations')
    if not isinstance(locations, list):
        # It might be under a different key, let's try 'location'
        locations = records.get('location')
        if not isinstance(locations, list):
            return

    for county_group in locations:
        if not isinstance(county_group, dict):
            continue
        
        # Townships are in a nested 'Location' list
        townships = county_group.get('Location')
        if isinstance(townships, list):
            for township in townships:
                if isinstance(township, dict):
                    yield township


def get_forecast_for_township(township_name: str, all_cwa_data: dict):
    """
    Extracts and processes CWA forecast data for a specific township.

    Args:
        township_name: The full name of the township (e.g., "臺北市中正區").
        all_cwa_data: The full JSON response from the CWA township forecast API.

    Returns:
        A dictionary containing the processed forecast, or None if not found.
    """
    if not all_cwa_data or 'records' not in all_cwa_data:
        print("Error: CWA data is invalid or empty.")
        return None

    records = all_cwa_data['records']
    cwa_location_data = None
    for loc in _iter_all_locations(records):
        name = loc.get('locationName') or loc.get('LocationName')
        print(f"Checking location: {name}") # DEBUG PRINT
        if _is_location_match(township_name, name):
            cwa_location_data = loc
            break
    
    if not cwa_location_data:
        sample_names = []
        for i, loc in enumerate(_iter_all_locations(records)):
            name = loc.get('locationName') or loc.get('LocationName')
            if name:
                sample_names.append(name)
            if i >= 9:
                break
        print(f"Error: Township '{township_name}' not found in CWA data. Sample available names: {sample_names}")
        return None


    # 2) Extract weather elements
    weather_elements = {}
    for element in cwa_location_data.get('weatherElement', []):
        element_name = element.get('elementName')
        element_value = "N/A"
        time_arr = element.get('time') or []
        if time_arr:
            first = time_arr[0]
            if isinstance(first, dict) and 'elementValue' in first and first['elementValue']:
                ev = first['elementValue'][0]
                if element_name == "天氣現象":
                    element_value = ev.get("Weather")
                elif element_name == "12小時降雨機率":
                    element_value = ev.get("ProbabilityOfPrecipitation")
                elif element_name == "平均溫度":
                    element_value = ev.get("Temperature")
        if element_name:
            weather_elements[element_name] = element_value

    # 3) Build response
    return {
        "township": township_name,
        "cwa_forecast": {
            "temperature": weather_elements.get("平均溫度"),
            "chance_of_rain_12h": weather_elements.get("12小時降雨機率"),
            "weather_description": weather_elements.get("天氣現象"),
        },
    }


def list_township_names(all_cwa_data: dict, limit: int = 200):
    names = []
    if not isinstance(all_cwa_data, dict):
        return names
    records = all_cwa_data.get('records')
    if not records:
        return names
    for loc in _iter_all_locations(records):
        if isinstance(loc, dict):
            name = loc.get('locationName') or loc.get('LocationName')
            if name:
                names.append(name)
                if len(names) >= limit:
                    break
    return names
