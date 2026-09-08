"""
پاکسازی متن و مدیریت تگ‌ها
"""
import re


class TextCleaner:
    def __init__(self, target_tag):
        self.target_tag = target_tag

    def clean(self, text):
        """پاکسازی کامل متن از تگ‌ها و لینک‌های تلگرامی"""
        if not text:
            return ""

        text = re.sub(r'https?://t\.me/\+?\w+', '', text, flags=re.IGNORECASE)
        text = re.sub(r't\.me/\+?\w+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'https?://t\.me/joinchat/\S+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'https?://t\.me/\+\S+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Forwarded from.*?\n', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'ارسال شده از.*?\n', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()

        return text

    def add_tag(self, text):
        """اضافه کردن تگ کانال مقصد به انتهای متن"""
        if not text:
            return f"@{self.target_tag}"
        return f"{text}\n\n@{self.target_tag}"

    def extract_caption(self, text, max_length=1024):
        """برش کپشن برای محدودیت تلگرام"""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
