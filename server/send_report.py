import requests
import json
from services import discord_sender

def send_weather_report():
    """
    Fetches weather data for a specific township and sends a report to Discord.
    """
    api_url = "http://127.0.0.1:8000/api/weather/?township_code=TPE-100"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        
        # Format the message
        message = f"""
        **Weather Report for {data['township']}**

        **CWA Forecast:**
        - Temperature: {data['cwa_forecast']['temperature']}
        - Weather: {data['cwa_forecast']['weather_description']}

        **Image Analysis:**
        - 12h Rain Chance: {data.get('chance_of_rain_12h', 'N/A')}
        - QPF 12h (min/max): {data.get('qpf12_min_mm_per_hr', 'N/A')} / {data.get('qpf12_max_mm_per_hr', 'N/A')}
        - QPF 6h (min/max): {data.get('qpf6_min_mm_per_hr', 'N/A')} / {data.get('qpf6_max_mm_per_hr', 'N/A')}
        - AQI Level: {data.get('aqi_level', 'N/A')}
        """
        
        discord_sender.send_to_discord(message)
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error processing weather data: {e}")

if __name__ == "__main__":
    send_weather_report()
