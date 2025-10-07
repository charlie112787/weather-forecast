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

# 縣市級預報 (F-C0032-001: 22 縣市)
CWA_COUNTY_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={CWA_API_KEY}"
# 鄉鎮級預報 (F-D0047-073: 368 鄉鎮/區) - 這是解決您之前錯誤的關鍵
CWA_TOWNSHIP_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-073?Authorization={CWA_API_KEY}"

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

# NCDR Nowcast URL pattern (checks for the first hour image to find the series)
NCDR_NOWCAST_URL_PATTERN = ["https://watch.ncdr.nat.gov.tw/00_Wxmap/7F17_NCDRQPF_12H/%Y%m/%Y%m%d/%Y%m%d%H/%Y%m%d%H_f01h.gif"]

# Crop/sample boxes (left,upper,right,lower). Set to None or a 4-tuple.
RAIN_PROBABILITY_CROP_BOX = None
AQI_SAMPLE_BOX = None

# Specific crop boxes for PoP12/PoP6 if they reside in different regions of the same image
POP12_CROP_BOX = None
POP6_CROP_BOX = None

# Optional path to Tesseract executable (Windows)
TESSERACT_CMD = ""

# HTTP/TLS settings
# 由於中央氣象署的 SSL 憑證問題，暫時關閉 SSL 驗證
REQUESTS_VERIFY_SSL = False

# SSL 錯誤時的 fallback 設置
ALLOW_INSECURE_FALLBACK = True

# 禁用 urllib3 的不安全請求警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- QPF Color Map and Sampling Coordinates ---
# Map representative RGB colors (as tuples) to rainfall intensity (mm/hr).
# Calibrate these values to match the legend of the CWA QPF images you use.
QPF_COLOR_MAP = {
    # (R, G, B): 降雨強度 (mm/hr)
    # 0.0 mm/hr
    (0, 0, 0): 0.0,             # 黑色 (背景/無資料)
    (255, 255, 255): 0.0,       # 白色 (背景/無雨) 
    
    # 0.5 - 2 mm/hr (微弱降雨)
    (170, 250, 160): 0.5,       # 極淺綠 (Light Green)
    (0, 220, 0): 1.0,           # 鮮綠色 (Green)
    
    # 2 - 8 mm/hr (一般降雨)
    (0, 190, 255): 3.0,         # 藍色 (Cyan/Light Blue)
    (0, 0, 255): 6.0,           # 深藍色 (Blue)
    
    # 8 - 20 mm/hr (強降雨)
    (255, 255, 0): 12.0,        # 黃色 (Yellow)
    (255, 128, 0): 15.0,        # 橘色 (Orange)
    (255, 0, 0): 25.0,          # 紅色 (Red)
    
    # > 20 mm/hr (極端降雨)
    (255, 0, 255): 40.0,        # 紫色 (Magenta)
    (128, 0, 128): 60.0,        # 深紫 (Dark Magenta)
}

# Per-county pixel coordinates for sampling on the QPF map.
# Coordinates are (x, y) in pixels.
IMAGE_SAMPLE_COORDS = {
    # 縣市名稱 : (X 像素座標, Y 像素座標)
    # 北部
    "基隆市": (400, 130),
    "臺北市": (360, 170),
    "新北市": (330, 220),
    "桃園市": (280, 260),
    "新竹市": (240, 320),
    "新竹縣": (260, 350),
    
    # 中部
    "苗栗縣": (240, 420),
    "臺中市": (230, 480),
    "彰化縣": (200, 550),
    "南投縣": (270, 560),
    "雲林縣": (200, 620),
    
    # 南部
    "嘉義市": (200, 670),
    "嘉義縣": (230, 700),
    "臺南市": (200, 780),
    "高雄市": (200, 850),
    "屏東縣": (230, 930),
    
    # 東部
    "宜蘭縣": (420, 320),
    "花蓮縣": (400, 600),
    "臺東縣": (350, 900),
    
    # 離島
    "澎湖縣": (50, 750),
    "金門縣": (50, 300),
    "連江縣": (30, 100), # 馬祖
}

# --- NCDR Nowcast Color Map (Placeholder) ---
# This is a placeholder copied from QPF_COLOR_MAP. 
# Calibrate these values to match the legend of the NCDR nowcast images.
NCDR_NOWCAST_COLOR_MAP = QPF_COLOR_MAP.copy()