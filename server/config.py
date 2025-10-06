import os

# --- Path Configuration ---
# Dynamically construct the absolute path to the service account key,
# assuming it is in the same directory as this config file.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.path.join(BASE_DIR, "serviceAccountKey.json")
# --- End of Path Configuration ---

# CWA API Authorization Key
CWA_API_KEY = os.getenv("CWA_API_KEY", "YOUR_CWA_API_KEY_HERE")

# NCDR API Details (User needs to provide these)
NCDR_API_BASE_URL = os.getenv("NCDR_API_BASE_URL", "YOUR_NCDR_API_URL_HERE")
NCDR_API_KEY = os.getenv("NCDR_API_KEY", "YOUR_NCDR_API_KEY_HERE")