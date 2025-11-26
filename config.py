import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Screener Settings
MAX_CANDIDATES = 50
MIN_RS_SCORE = 70  # Percentile for Relative Strength
RSI_THRESHOLD = 70
MIN_PRICE = 10.0

# Paths
DATA_DIR = "data"
CHARTS_DIR = "charts"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)
