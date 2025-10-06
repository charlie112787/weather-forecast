
import sys
import os
import json

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.core.data_fetcher import get_cwa_county_forecast_data

def main():
    # 1. Get all CWA county data
    all_data = get_cwa_county_forecast_data()
    if not all_data:
        print("Could not fetch weather data.")
        return

    # 2. Save all data to a file
    with open("cwa_county_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print("Data saved to cwa_county_data.json")

if __name__ == "__main__":
    main()
