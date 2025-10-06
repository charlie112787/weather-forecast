import requests
from server import config

def send_to_discord(message: str):
    """
    Sends a message to the Discord webhook URL specified in the config.

    Args:
        message: The string message to send.
    """
    if not config.DISCORD_WEBHOOK_URL or "discord.com" not in config.DISCORD_WEBHOOK_URL:
        # print("Discord webhook URL not configured or invalid. Skipping.")
        return

    payload = {"content": message}
    
    try:
        response = requests.post(config.DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Successfully sent message to Discord.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Discord: {e}")
