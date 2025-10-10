import sys
import os
import json

from core.data_fetcher import get_cwa_township_forecast_data
from core.calculation import _is_location_match

def get_township_weather(township_name, county_name, township_data):
    if not township_data or 'records' not in township_data:
        return None

    for county in township_data['records']['locations']:
        if _is_location_match(county_name, county.get('locationsName')):
            for loc in county['location']:
                if _is_location_match(township_name, loc.get('locationName')):
                    for element in loc['weatherElement']:
                        if element['elementName'] == 'Wx':
                            return element['time'][0]['parameter']['parameterName']
    return None

def main():
    county_name = "臺北市"
    township_name = "中正區"

    # 1. Fetch data
    township_data = get_cwa_township_forecast_data()

    if not township_data:
        print("Could not fetch weather data.")
        return

    # 2. Get weather description from township data
    weather_description = get_township_weather(township_name, county_name, township_data)

    print(f"Weather for {county_name}{township_name}: {weather_description}")


if __name__ == "__main__":
    main()