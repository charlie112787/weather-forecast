import os

# CWA API Authorization Key
CWA_API_KEY = os.getenv("CWA_API_KEY", "CWA-F3565C7E-B3CB-42AF-B86E-E882A5DAF79F")

# NCDR API Details (User needs to provide these)
NCDR_API_BASE_URL = os.getenv("NCDR_API_BASE_URL", "YOUR_NCDR_API_URL_HERE")
NCDR_API_KEY = os.getenv("NCDR_API_KEY", "YOUR_NCDR_API_KEY_HERE")

# Firebase Service Account Key
FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "path/to/your/serviceAccountKey.json")
