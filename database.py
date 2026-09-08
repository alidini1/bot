"""
مدیریت دیتابیس SQLite
"""
import sqlite3
import hashlib
from datetime import datetime, timedelta
from difflib import SequenceMatcher


class Database:
    def __init__(self, db_path="bot.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS channel_states (
            channel_id TEXT PRIMARY KEY,
            last_message_id INTEGER DEFAULT 0,
            updated_at TIMESTAMP
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS processed_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_hash TEXT,
            clean_text TEXT,
            created_at TIMESTAMP,
            channel_id TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS stats (
            date TEXT PRIMARY KEY,
            total_processed INTEGER DEFAULT 0,
            gemini_success INTEGER DEFAULT 0,
            gemini_failed INTEGER DEFAULT 0,
            duplicates_blocked INTEGER DEFAULT 0
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS source_channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT,
            added_at TIMESTAMP
        )''')

        conn.commit()
        conn.close()

    def get_last_message_id(self, channel_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT last_message_id FROM channel_states WHERE channel_id = ?", (str(channel_id),))
        result = c.fetchone()
        conn.close()
        return result[0] if result else 0

    def update_last_message_id(self, channel_id, message_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO channel_states (channel_id, last_message_id, updated_at)
                     VALUES (?, ?, ?)''', (str(channel_id), message_id, datetime.now()))
        conn.commit()
        conn.close()

    def add_processed_message(self, clean_text, channel_id):
        content_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO processed_messages (content_hash, clean_text, created_at, channel_id)
                     VALUES (?, ?, ?, ?)''', (content_hash, clean_text, datetime.now(), str(channel_id)))
        conn.commit()
        conn.close()

    def is_duplicate(self, clean_text, threshold=0.82, hours=24):
        content_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT 1 FROM processed_messages WHERE content_hash = ?", (content_hash,))
        if c.fetchone():
            conn.close()
            return True, "exact"

        since = datetime.now() - timedelta(hours=hours)
        c.execute("SELECT clean_text FROM processed_messages WHERE created_at > ?", (since,))
        rows = c.fetchall()
        conn.close()

        for (existing_text,) in rows:
            if not existing_text:
                continue
            similarity = SequenceMatcher(None, clean_text, existing_text).ratio()
            if similarity >= threshold:
                return True, f"similarity_{similarity:.2f}"

        return False, None

    def cleanup_old_messages(self, hours=48):
        since = datetime.now() - timedelta(hours=hours)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM processed_messages WHERE created_at < ?", (since,))
        conn.commit()
        conn.close()

    def add_source_channel(self, channel_id, channel_name):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO source_channels (channel_id, channel_name, added_at)
                     VALUES (?, ?, ?)''', (str(channel_id), channel_name, datetime.now()))
        conn.commit()
        conn.close()

    def remove_source_channel(self, channel_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM source_channels WHERE channel_id = ?", (str(channel_id),))
        conn.commit()
        conn.close()

    def get_source_channels(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT channel_id, channel_name FROM source_channels")
        rows = c.fetchall()
        conn.close()
        return rows

    def increment_stat(self, field, date=None):
        date = date or datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(f'''INSERT INTO stats (date, {field}) VALUES (?, 1)
                      ON CONFLICT(date) DO UPDATE SET {field} = {field} + 1''', (date,))
        conn.commit()
        conn.close()

    def get_stats(self, days=7):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        c.execute('''SELECT date, total_processed, gemini_success, gemini_failed, duplicates_blocked
                     FROM stats WHERE date >= ? ORDER BY date DESC''', (since,))
        rows = c.fetchall()
        conn.close()
        return rows

    def get_total_stats(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT 
            COALESCE(SUM(total_processed), 0),
            COALESCE(SUM(gemini_success), 0),
            COALESCE(SUM(gemini_failed), 0),
            COALESCE(SUM(duplicates_blocked), 0)
            FROM stats''')
        result = c.fetchone()
        conn.close()
        return result
