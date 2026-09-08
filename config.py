"""
تنظیمات اصلی ربات
"""
import os

API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH", "your_api_hash_here")
SESSION_STRING = os.getenv("SESSION_STRING", "")

TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "@your_target_channel")
TARGET_CHANNEL_TAG = os.getenv("TARGET_CHANNEL_TAG", "your_target_channel")

_raw_sources = os.getenv("SOURCE_CHANNELS", "")
SOURCE_CHANNELS = [s.strip() for s in _raw_sources.split(",") if s.strip()]

# Gemini keys — support comma OR newline separated
#_raw_keys = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS =[ "AQ.Ab8RN6KPiDYS3mJ-38Dxp0rswktL9-UoGEpjsYha4rzfDBdESg",
    "AQ.Ab8RN6IpXydlIjcdN7f4L7oVvXYpnG5TO1TBdYxdlZFvL1qPWw",
    "AQ.Ab8RN6JuouR_WIVm6VPblQALUJ612y4bHrmjEvUmANJMk29pHg",
    "AQ.Ab8RN6JCLHtWre-hVZpesTziVWlJoKpZ7yyxJlsR-86o6uiJ7g",
    ]

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

RANDOM_DELAY_MIN = int(os.getenv("RANDOM_DELAY_MIN", "5"))
RANDOM_DELAY_MAX = int(os.getenv("RANDOM_DELAY_MAX", "15"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.82"))
DUPLICATE_TIME_WINDOW_HOURS = int(os.getenv("DUPLICATE_TIME_WINDOW_HOURS", "24"))

_raw_filter = os.getenv("FILTER_KEYWORDS", "")
FILTER_KEYWORDS = [k.strip() for k in _raw_filter.split(",") if k.strip()]
