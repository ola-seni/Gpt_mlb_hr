# config.py

import os
from datetime import datetime

# API Keys
OPENWEATHER_API = os.getenv("OPENWEATHER_API")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Date Ranges
CURRENT_YEAR = datetime.now().year
if CURRENT_YEAR >= 2025:
    # Use current season
    SEASON_START = f"{CURRENT_YEAR}-03-01"
    SEASON_END = datetime.now().strftime("%Y-%m-%d")
else:
    # Use previous season for testing/development
    SEASON_START = "2023-04-01"
    SEASON_END = "2023-10-01"

# Prediction Parameters
HR_SCORE_THRESHOLDS = {
    "LOCK": 0.25,
    "SLEEPER": 0.15,
    "RISKY": 0.0
}

# Cache Settings
CACHE_MAX_AGE_DAYS = 30

# File Paths
RESULTS_DIR = "results"
CACHE_DIR = "cache"
MODEL_PATH = "model.pkl"

# Ensure directories exist
for directory in [RESULTS_DIR, CACHE_DIR]:
    os.makedirs(directory, exist_ok=True)
