"""
تشخیص پیام تکراری (Exact + Similarity)
"""


class DuplicateDetector:
    def __init__(self, db, threshold=0.82, hours=24):
        self.db = db
        self.threshold = threshold
        self.hours = hours

    def is_duplicate(self, clean_text):
        """بررسی تکراری بودن پیام"""
        return self.db.is_duplicate(clean_text, self.threshold, self.hours)

    def add_message(self, clean_text, channel_id):
        """ثبت پیام جدید در دیتابیس"""
        self.db.add_processed_message(clean_text, channel_id)
