
import datetime
from server.scheduler import jobs
from server.core import codes

def generate_json_output():
    """
    Generates the final JSON output by combining CWA and AQI data.
    """
    update_time = datetime.datetime.now().isoformat()
    
    cwa_county_data = jobs.get_cached_cwa_county_data()
    cwa_township_data = jobs.get_cached_cwa_township_data()
    image_metrics = jobs.get_cached_image_metrics()
    
    if not cwa_county_data or not cwa_township_data:
        return None
        
    final_json = {
        "update_time": update_time,
    }
    
    # Helper to extract the first parameter name from a weather element
    def get_weather_element(elements, element_name):
        for element in elements:
            if element.get('elementName') == element_name:
                time_entry = element.get('time', [{}])[0]
                parameter = time_entry.get('parameter', {})
                return parameter.get('parameterName')
        return None

    # Helper to extract rain probability from township data
    def get_town_rain_prob(town_weather_element, pop_element_name):
        for element in town_weather_element:
            if element.get('elementName') == pop_element_name:
                time_entry = element.get('time', [{}])[0]
                if 'elementValue' in time_entry:
                    return time_entry['elementValue'][0].get('value')
        return None

    # Process county data
    for county in cwa_county_data.get('records', {}).get('location', []):
        county_name = county.get('locationName')
        county_code = codes.COUNTY_NAME_TO_CODE.get(county_name)
        
        if not county_code:
            continue
            
        weather_elements = county.get('weatherElement', [])
        
        # Calculate average temperature
        min_temp_str = get_weather_element(weather_elements, 'MinT')
        max_temp_str = get_weather_element(weather_elements, 'MaxT')
        
        avg_temp = None
        if min_temp_str and max_temp_str:
            try:
                avg_temp = (float(min_temp_str) + float(max_temp_str)) / 2
            except (ValueError, TypeError):
                avg_temp = None

        final_json[county_code] = {
            "name": county_name,
            "temp": avg_temp,
            "weather": get_weather_element(weather_elements, 'Wx'),
            "rain_6h": None, # Placeholder, will be populated from township data
            "rain_12h": None, # Placeholder, will be populated from township data
            "aqi": image_metrics.get('aqi_level') if image_metrics else None,
            "towns": {}
        }

    # Process township data
    if cwa_township_data.get('records'):
        locations = cwa_township_data['records'].get('locations', [])
        for county_towns in locations:
            county_name = county_towns.get('locationsName')
            county_code = codes.COUNTY_NAME_TO_CODE.get(county_name)

            if not county_code or county_code not in final_json:
                continue

            town_rain_6h = []
            town_rain_12h = []

            for town in county_towns.get('location', []):
                town_name = town.get('locationName')
                town_code = codes.TOWNSHIP_NAME_TO_CODE.get(f"{county_name}{town_name}")
                
                if not town_code:
                    continue

                weather_element = town.get('weatherElement', [])
                rain_6h_str = get_town_rain_prob(weather_element, '6小時降雨機率')
                rain_12h_str = get_town_rain_prob(weather_element, '12小時降雨機率')

                rain_6h = int(rain_6h_str) if rain_6h_str and rain_6h_str.isdigit() else None
                rain_12h = int(rain_12h_str) if rain_12h_str and rain_12h_str.isdigit() else None
                
                if rain_6h is not None:
                    town_rain_6h.append(rain_6h)
                
                if rain_12h is not None:
                    town_rain_12h.append(rain_12h)

                final_json[county_code]['towns'][town_code] = {
                    "rain_6h": rain_6h,
                    "rain_12h": rain_12h,
                }
            
            # Calculate average rain probability for the county
            if town_rain_6h:
                final_json[county_code]['rain_6h'] = sum(town_rain_6h) / len(town_rain_6h)
            if town_rain_12h:
                final_json[county_code]['rain_12h'] = sum(town_rain_12h) / len(town_rain_12h)

    return final_json
