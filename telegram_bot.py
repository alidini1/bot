"""
هسته اصلی ربات تلگرام — Event-driven + Railway Compatible
"""
import asyncio
import random
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.types import PeerChannel
from telethon.utils import get_peer_id

from config import *
from database import Database
from gemini_client import GeminiClient
from text_cleaner import TextCleaner
from duplicate_detector import DuplicateDetector


class NewsBot:
    def __init__(self):
        if SESSION_STRING:
            session = StringSession(SESSION_STRING)
            print("[INIT] Using Session String")
        else:
            session = SESSION_NAME
            print("[INIT] Using Session File: " + str(session))

        self.client = TelegramClient(session, API_ID, API_HASH)
        self.db = Database()
        self.gemini = GeminiClient(GEMINI_API_KEYS, GEMINI_MODEL)
        self.cleaner = TextCleaner(TARGET_CHANNEL_TAG)
        self.duplicate = DuplicateDetector(self.db, SIMILARITY_THRESHOLD, DUPLICATE_TIME_WINDOW_HOURS)
        self.running = False
        self._pending_albums = {}
        self._album_timers = {}
        self._resolved_sources = {}
        self._handlers_set = False

        # ثبت کانال‌های اولیه از config توی دیتابیس
        self._init_source_channels()

    def _init_source_channels(self):
        """کانال‌های SOURCE_CHANNELS رو توی دیتابیس ثبت کن"""
        for ch in SOURCE_CHANNELS:
            self.db.add_source_channel(ch, ch)
        print("[INIT] Registered " + str(len(SOURCE_CHANNELS)) + " source channels from config")

    def _format_message(self, title, body, hashtags):
        lines = []
        lines.append("<b>" + self._escape_html(title) + "</b>")
        lines.append("")
        lines.append("<code>━━━━━━━━━━━━━━━━━━━━</code>")
        lines.append("")
        lines.append(self._escape_html(body))
        lines.append("")
        lines.append("<code>━━━━━━━━━━━━━━━━━━━━</code>")
        lines.append("")
        if hashtags:
            parts = hashtags.split()
            ht = " ".join(["<i>" + self._escape_html(h) + "</i>" for h in parts])
            lines.append(ht)
            lines.append("")
        lines.append('<a href="https://t.me/' + TARGET_CHANNEL_TAG + '">@' + TARGET_CHANNEL_TAG + "</a>")
        return "\n".join(lines)

    def _escape_html(self, text):
        if not text:
            return ""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _parse_gemini_output(self, raw):
        title = ""
        body = ""
        hashtags = ""
        t_match = re.search(r"<TITLE>\s*(.*?)\s*</TITLE>", raw, re.DOTALL)
        if t_match:
            title = t_match.group(1).strip()
        b_match = re.search(r"<BODY>\s*(.*?)\s*</BODY>", raw, re.DOTALL)
        if b_match:
            body = b_match.group(1).strip()
        h_match = re.search(r"<HASHTAGS>\s*(.*?)\s*</HASHTAGS>", raw, re.DOTALL)
        if h_match:
            hashtags = h_match.group(1).strip()
        return title, body, hashtags

    async def _resolve_source_channels(self):
        channels = self.db.get_source_channels()
        self._resolved_sources = {}
        print("[Resolve] Found " + str(len(channels)) + " channels in DB")
        for cid, cname in channels:
            try:
                int_id = int(cid)
                marked = get_peer_id(PeerChannel(int_id))
                self._resolved_sources[cid] = {"bare": int_id, "marked": marked, "username": ""}
                print("[Resolve] OK numeric " + cname + " marked=" + str(marked))
            except ValueError:
                try:
                    entity = await self.client.get_entity(cid)
                    bare_id = entity.id
                    marked = get_peer_id(PeerChannel(bare_id))
                    username = getattr(entity, 'username', '') or ''
                    self._resolved_sources[cid] = {"bare": bare_id, "marked": marked, "username": username}
                    self.db.remove_source_channel(cid)
                    self.db.add_source_channel(str(bare_id), cname)
                    print("[Resolve] OK username " + cname + " @" + username + " marked=" + str(marked))
                except Exception as e:
                    print("[Resolve] FAIL " + cid + ": " + str(e))
        print("[Resolve] Total resolved: " + str(len(self._resolved_sources)))

    def _is_source_channel(self, event):
        chat_id = event.chat_id
        chat_bare_id = event.chat.id if event.chat else None
        chat_username = (getattr(event.chat, 'username', '') or '').lower()

        for cid, info in self._resolved_sources.items():
            if chat_id == info["marked"]:
                return True
            if chat_bare_id is not None and chat_bare_id == info["bare"]:
                return True
            if chat_username and chat_username == info["username"].lower():
                return True
            if chat_username and chat_username == cid.lower().lstrip('@'):
                return True
        return False

    def _setup_handlers(self):
        if self._handlers_set:
            return
        self._handlers_set = True
        print("[Handlers] Setting up...")

        @self.client.on(events.NewMessage(pattern=r"/start"))
        async def start_handler(event):
            if event.is_private:
                await event.reply(
                    "👋 <b>سلام!</b> ربات مدیریت خبر فعال است.\n\n"
                    "دستورات مدیریتی:\n"
                    "<code>/addchannel @channel</code> — اضافه کردن کانال\n"
                    "<code>/removechannel @channel</code> — حذف کانال\n"
                    "<code>/listchannels</code> — لیست کانال‌ها\n"
                    "<code>/stats</code> — آمار کلی\n"
                    "<code>/statsday</code> — آمار امروز",
                    parse_mode="html"
                )

        @self.client.on(events.NewMessage(pattern=r"/addchannel (.+)"))
        async def add_channel(event):
            if not event.is_private:
                return
            ch = event.pattern_match.group(1).strip()
            try:
                entity = await self.client.get_entity(ch)
                bare_id = entity.id
                cid = str(bare_id)
                name = getattr(entity, "username", ch) or ch
                self.db.add_source_channel(cid, name)
                marked = get_peer_id(PeerChannel(bare_id))
                username = getattr(entity, 'username', '') or ''
                self._resolved_sources[cid] = {"bare": bare_id, "marked": marked, "username": username}
                await event.reply("✅ کانال <b>" + name + "</b> اضافه شد.", parse_mode="html")
            except Exception as e:
                await event.reply("❌ خطا: <code>" + str(e) + "</code>", parse_mode="html")

        @self.client.on(events.NewMessage(pattern=r"/removechannel (.+)"))
        async def remove_channel(event):
            if not event.is_private:
                return
            ch = event.pattern_match.group(1).strip()
            try:
                entity = await self.client.get_entity(ch)
                cid = str(entity.id)
                self.db.remove_source_channel(cid)
                keys_to_remove = []
                for k, v in self._resolved_sources.items():
                    if v["bare"] == entity.id or k == ch:
                        keys_to_remove.append(k)
                for k in keys_to_remove:
                    self._resolved_sources.pop(k, None)
                await event.reply("✅ کانال <b>" + ch + "</b> حذف شد.", parse_mode="html")
            except Exception as e:
                await event.reply("❌ خطا: <code>" + str(e) + "</code>", parse_mode="html")

        @self.client.on(events.NewMessage(pattern=r"/listchannels"))
        async def list_channels(event):
            if not event.is_private:
                return
            channels = self.db.get_source_channels()
            if not channels:
                await event.reply("📭 هیچ کانال منبعی ثبت نشده.")
                return
            text = "📋 <b>کانال‌های منبع:</b>\n\n"
            for cid, name in channels:
                text += "• <code>" + name + "</code>\n"
            await event.reply(text, parse_mode="html")

        @self.client.on(events.NewMessage(pattern=r"/stats"))
        async def stats_handler(event):
            if not event.is_private:
                return
            total = self.db.get_total_stats()
            text = (
                "📊 <b>آمار کلی ربات</b>\n\n"
                "📨 کل پردازش شده: <code>" + str(total[0]) + "</code>\n"
                "✅ Gemini موفق: <code>" + str(total[1]) + "</code>\n"
                "❌ Gemini ناموفق: <code>" + str(total[2]) + "</code>\n"
                "🚫 تکراری بلاک: <code>" + str(total[3]) + "</code>"
            )
            await event.reply(text, parse_mode="html")

        @self.client.on(events.NewMessage(pattern=r"/statsday"))
        async def stats_day_handler(event):
            if not event.is_private:
                return
            rows = self.db.get_stats(days=1)
            if not rows:
                await event.reply("📊 امروز هنوز آماری ثبت نشده.")
                return
            date, p, g, f, d = rows[0]
            text = (
                "📊 <b>آمار " + date + "</b>\n\n"
                "📨 پردازش: <code>" + str(p) + "</code>\n"
                "✅ Gemini: <code>" + str(g) + "</code>\n"
                "❌ ناموفق: <code>" + str(f) + "</code>\n"
                "🚫 تکراری: <code>" + str(d) + "</code>"
            )
            await event.reply(text, parse_mode="html")

        @self.client.on(events.NewMessage)
        async def source_handler(event):
            if not event.is_channel:
                return
            chat_name = getattr(event.chat, 'username', str(event.chat_id)) or str(event.chat_id)
            print("[Event] Channel msg from: " + chat_name + " chat_id=" + str(event.chat_id))
            if not self._is_source_channel(event):
                print("[Event] SKIP " + str(event.chat_id) + " not in source list")
                return
            print("[Event] MATCH! Processing...")
            msg = event.message
            if msg.grouped_id:
                await self._handle_album(msg)
                return
            await self._process_message(msg)

        print("[Handlers] Setup complete.")

    async def _handle_album(self, msg):
        gid = msg.grouped_id
        if gid not in self._pending_albums:
            self._pending_albums[gid] = []
            async def process_album_after_delay():
                await asyncio.sleep(3)
                album = self._pending_albums.pop(gid, [])
                if album:
                    await self._process_album(album)
                self._album_timers.pop(gid, None)
            task = asyncio.create_task(process_album_after_delay())
            self._album_timers[gid] = task
        self._pending_albums[gid].append(msg)

    async def _process_message(self, msg):
        try:
            text = msg.message or ""
            clean_text = self.cleaner.clean(text)
            print("[Process] Clean text: " + clean_text[:80])
            if not clean_text and not msg.media:
                print("[Process] Empty, skip")
                return
            is_dup, reason = self.duplicate.is_duplicate(clean_text or "")
            if is_dup:
                print("[Process] Duplicate blocked: " + reason)
                self.db.increment_stat("duplicates_blocked")
                return
            if FILTER_KEYWORDS and clean_text:
                if not any(kw in clean_text for kw in FILTER_KEYWORDS):
                    print("[Process] Filtered by keywords")
                    return
            print("[Process] Calling Gemini...")
            gemini_raw = self.gemini.rewrite_and_hashtag(clean_text)
            if gemini_raw:
                print("[Process] Gemini OK")
                title, body, hashtags = self._parse_gemini_output(gemini_raw)
                self.db.increment_stat("gemini_success")
            else:
                print("[Process] Gemini FAIL, using fallback")
                title = ""
                body = clean_text
                hashtags = ""
                self.db.increment_stat("gemini_failed")
            if not title and body:
                lines = body.split("\n")
                title = lines[0][:100]
                body = "\n".join(lines[1:]) if len(lines) > 1 else ""
            final_html = self._format_message(title, body, hashtags)
            print("[Process] Sending to " + TARGET_CHANNEL)
            target = await self.client.get_entity(TARGET_CHANNEL)
            if msg.media:
                await self.client.send_file(target, msg.media, caption=final_html, parse_mode="html")
            else:
                await self.client.send_message(target, final_html, parse_mode="html")
            self.db.increment_stat("total_processed")
            if clean_text:
                self.duplicate.add_message(clean_text, msg.chat_id)
            print("[Process] SENT!")
            await asyncio.sleep(random.randint(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX))
        except FloodWaitError as e:
            print("[Process] FloodWait: " + str(e.seconds))
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print("[Process] ERROR: " + str(e))
            import traceback
            traceback.print_exc()

    async def _process_album(self, album_msgs):
        try:
            text = album_msgs[0].message or ""
            clean_text = self.cleaner.clean(text)
            is_dup, reason = self.duplicate.is_duplicate(clean_text or "")
            if is_dup:
                self.db.increment_stat("duplicates_blocked")
                return
            if FILTER_KEYWORDS and clean_text:
                if not any(kw in clean_text for kw in FILTER_KEYWORDS):
                    return
            gemini_raw = self.gemini.rewrite_and_hashtag(clean_text)
            if gemini_raw:
                title, body, hashtags = self._parse_gemini_output(gemini_raw)
                self.db.increment_stat("gemini_success")
            else:
                title = ""
                body = clean_text
                hashtags = ""
                self.db.increment_stat("gemini_failed")
            if not title and body:
                lines = body.split("\n")
                title = lines[0][:100]
                body = "\n".join(lines[1:]) if len(lines) > 1 else ""
            final_html = self._format_message(title, body, hashtags)
            target = await self.client.get_entity(TARGET_CHANNEL)
            media_files = [m.media for m in album_msgs if m.media]
            if media_files:
                await self.client.send_file(target, media_files, caption=final_html, parse_mode="html")
            else:
                await self.client.send_message(target, final_html, parse_mode="html")
            self.db.increment_stat("total_processed")
            if clean_text:
                self.duplicate.add_message(clean_text, album_msgs[0].chat_id)
            await asyncio.sleep(random.randint(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX))
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print("[Album] ERROR: " + str(e))
            import traceback
            traceback.print_exc()

    async def run(self):
        print("[Run] Starting client...")
        await self.client.start()
        me = await self.client.get_me()
        print("[Run] Logged in as: " + str(me.first_name) + " (" + str(me.id) + ")")
        await self._resolve_source_channels()
        self._setup_handlers()
        print("=" * 50)
        print("🚀 ربات خبر فعال شد!")
        print("📤 کانال مقصد: " + TARGET_CHANNEL)
        print("📡 کانال‌های منبع: " + str(len(self._resolved_sources)))
        print("=" * 50)
        self.running = True
        
        while self.running:
            try:
                print("[Run] Waiting for updates...")
                await self.client.run_until_disconnected()
            except Exception as e:
                print("[Run] Connection lost: " + str(e))
            if self.running:
                print("[Run] Reconnecting in 5s...")
                await asyncio.sleep(5)
                try:
                    if not self.client.is_connected():
                        await self.client.connect()
                        print("[Run] Reconnected!")
                except Exception as e2:
                    print("[Run] Reconnect failed: " + str(e2))
                    await asyncio.sleep(10)

    async def stop(self):
        self.running = False
        await self.client.disconnect()
        print("🛑 ربات متوقف شد.")
