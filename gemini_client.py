"""
کلاینت Gemini با requests (سبک، بدون grpcio/pydantic)
"""
import time
import requests


class GeminiClient:
    def __init__(self, api_keys, model="gemini-3.8-flash"):
        if not api_keys:
            raise ValueError("حداقل یک کلید Gemini لازم است!")
        self.api_keys = api_keys
        self.current_key_index = 0
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def _next_key(self):
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        print(f"[Gemini] Switched to key #{self.current_key_index + 1}")

    def _call_api(self, prompt):
        key = self.api_keys[self.current_key_index]
        url = f"{self.base_url}?key={key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.75,
                "maxOutputTokens": 2048,
            }
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return None
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return None
        return parts[0].get("text", "").strip()

    def rewrite_and_hashtag(self, text, retries_per_key=2):
        prompt = f"""تو یک ویراستار خبر حرفه‌ای با استایل تند، تیز و جذاب هستی. مخاطب تو جوانان فارسی‌زبان تلگرام هستن.

📌 قوانین کلی:
1. متن رو به شکل یک خبر رسمی ولی جذاب و خواندنی بازنویسی کن
2. هرگز از هیچ حکومت یا گروه سیاسی خاصی تعریف نکن — صرفاً واقعیت رو بنویس
3. اگه خبر مربوط به کشور خاصیه، پرچم اون کشور 🇮🇷 🇺🇸 🇮🇱 🇨🇳 🇷🇺 🇹🇷 🇬🇧 رو اول عنوان بذار
4. اگه فردی حرفی زده یا اظهارنظری کرده، حتماً به صورت نقل قول مستقیم (با علامت «») بیارش
6. ۳ تا ۵ هشتگ فارسی مرتبط بذار

🎭 استایل و لحن:
• گاهی (نه همیشه) اگه موضوعش جدی نیست، یه کنایه یا طنز ملایم بکار ببر
• از کلمات خشک خبری مثل «بنا به گزارش‌ها»، «شایان ذکر است»، «لازم به ذکر است» پرهیز کن
• جملات کوتاه و پرقدرت بنویس
• از ایموجی استفاده کن ولی نه زیاد — فقط جاهایی که حسش هست

📐 فرمت خروجی (دقیقاً همین تگ‌ها رو رعایت کن):

<TITLE>
[پرچم کشور اگه هست] عنوان خبر (یک جمله کوتاه، گیرا و کلیک‌خور)
</TITLE>

<BODY>
متن خبر بازنویسی‌شده

اگه کسی حرفی زده:
فلانی گفت: «نقل قول مستقیم اینجا»

ادامه متن...
</BODY>

<HASHTAGS>
#هشتگ1 #هشتگ2 #هشتگ3
</HASHTAGS>

⚠️ مهم: فقط و فقط متن بین تگ‌ها رو برگردون. هیچ توضیحی قبل یا بعدش ننویس.

متن ورودی:
{text}
"""
        max_attempts = retries_per_key * len(self.api_keys)

        for attempt in range(max_attempts):
            try:
                result = self._call_api(prompt)
                if result:
                    return result
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else 0
                print(f"[Gemini] HTTP {status}: {e}")
                if status in (429, 400, 401, 403):
                    self._next_key()
                    time.sleep(1)
                else:
                    time.sleep(2)
            except Exception as e:
                print(f"[Gemini] Error: {e}")
                time.sleep(2)

        print("[Gemini] All keys failed!")
        return None
