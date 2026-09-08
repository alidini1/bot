"""
تنظیمات اصلی ربات
----------------
قبل از اجرا حتماً مقادیر زیر را پر کنید یا از Environment Variables استفاده کنید.
"""
import os

# ─── تلگرام ───
API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH", "your_api_hash_here")

# 🔑 Session String (برای Railway/Termux بدون فایل .session)
# با python get_session.py می‌تونی بگیری
SESSION_STRING = os.getenv("SESSION_STRING", "")

# ─── کانال‌ها ───
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "@your_target_channel")
TARGET_CHANNEL_TAG = os.getenv("TARGET_CHANNEL_TAG", "your_target_channel")

_raw_sources = os.getenv("SOURCE_CHANNELS", "")
SOURCE_CHANNELS = [s.strip() for s in _raw_sources.split(",") if s.strip()]

# ─── Gemini ───
_raw_keys = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS = [k.strip() for k in _raw_keys.split(",") if k.strip()]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# ─── تنظیمات عملکرد ───
RANDOM_DELAY_MIN = int(os.getenv("RANDOM_DELAY_MIN", "5"))
RANDOM_DELAY_MAX = int(os.getenv("RANDOM_DELAY_MAX", "15"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.82"))
DUPLICATE_TIME_WINDOW_HOURS = int(os.getenv("DUPLICATE_TIME_WINDOW_HOURS", "24"))

_raw_filter = os.getenv("FILTER_KEYWORDS", "")
FILTER_KEYWORDS = [k.strip() for k in _raw_filter.split(",") if k.strip()]
