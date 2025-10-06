# --- Image Analysis Settings (edit directly) ---
import os

# --- Path Configuration ---
# Dynamically construct the absolute path to the service account key,
# assuming it is in the same directory as this config file.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.path.join(BASE_DIR, "serviceAccountKey.json")
# --- End of Path Configuration ---

# CWA API Authorization Key (edit directly here)
CWA_API_KEY = "CWA-F3565C7E-B3CB-42AF-B86E-E882A5DAF79F"

# NCDR API Details (edit directly if used)
NCDR_API_BASE_URL = "YOUR_NCDR_API_URL_HERE"
NCDR_API_KEY = "YOUR_NCDR_API_KEY_HERE"

# Discord Webhook URL (edit directly if used)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1424684753357111369/Cgo20EKHKCZd3eO9wJUDQmLtsTlupgTgTiA1fJyFR667cAqWAo8HeHCRyjpYKcyYLXVt"

# --- Image Analysis Settings (edit directly) ---
# URLs for rain probability and AQI images to analyze
RAIN_PROBABILITY_IMAGE_URL = ""
AQI_IMAGE_URL = ""

# Separate images for 12h and 6h PoP if provided (fallback to RAIN_PROBABILITY_IMAGE_URL)
POP12_IMAGE_URL = RAIN_PROBABILITY_IMAGE_URL
POP6_IMAGE_URL = RAIN_PROBABILITY_IMAGE_URL

# If the URLs are dynamic, provide strftime patterns here; resolver will try the latest.
# Examples (you should replace with real patterns when known):
#   "https://example.cwa.gov.tw/pop12_%Y%m%d%H.png"
#   "https://example.cwa.gov.tw/pop6_%Y%m%d%H.png"
POP12_URL_PATTERNS = ["https://npd.cwa.gov.tw/NPD/image/BC_QPF_12_%Y%m%d%H.png"]  # type: ignore[var-annotated]
POP6_URL_PATTERNS = ["https://npd.cwa.gov.tw/NPD/image/BC_QPF_06_%Y%m%d%H.png"]   # type: ignore[var-annotated]
AQI_URL_PATTERNS = ["https://airtw.epa.gov.tw/EnvStatus/map_static_img/AQI_Day.png"]    # type: ignore[var-annotated]

# Crop/sample boxes (left,upper,right,lower). Set to None or a 4-tuple.
RAIN_PROBABILITY_CROP_BOX = None
AQI_SAMPLE_BOX = None

# Specific crop boxes for PoP12/PoP6 if they reside in different regions of the same image
POP12_CROP_BOX = None
POP6_CROP_BOX = None

# Optional path to Tesseract executable (Windows)
TESSERACT_CMD = ""

# HTTP/TLS settings
# If True (default), requests will verify HTTPS certificates.
# Set to False ONLY if you encounter local CA issues and understand the risk.
REQUESTS_VERIFY_SSL = True

# If True, when a SSL error occurs for CWA API, allow one retry with verify=False.
# Keep False unless you are blocked by local CA issues.
ALLOW_INSECURE_FALLBACK = True

# --- QPF Color Map and Sampling Coordinates ---
# Map representative RGB colors (as tuples) to rainfall intensity (mm/hr).
# Calibrate these values to match the legend of the CWA QPF images you use.
QPF_COLOR_MAP = {
    (0, 0, 255): 0.5,
    (0, 255, 255): 1.0,
    (0, 255, 0): 5.0,
    (255, 255, 0): 10.0,
    (255, 165, 0): 20.0,
    (255, 0, 0): 40.0,
    (128, 0, 128): 80.0,
}

# Per-county pixel coordinates for sampling on the QPF map.
# Coordinates are (x, y) in pixels.
IMAGE_SAMPLE_COORDS = {
    "臺北市": (900, 450),
    "新北市": (860, 460),
    "桃園市": (820, 480),
}