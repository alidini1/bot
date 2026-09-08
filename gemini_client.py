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
                "temperature": 0.6,
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
        prompt = f"""شما یک ویراستار خبر حرفه‌ای و کاملاً بی‌طرف هستید.

قوانین سختگیرانه:
1. متن را به صورت خبری رسمی، روان و جذاب بازنویسی کنید
2. هرگز از هیچ حکومت، دولت یا گروه سیاسی خاصی تعریف نکنید
3. اگر خبر مربوط به جمهوری اسلامی یا مقامات آن بود، صرفاً واقعیت را بدون جانبداری بنویسید
4. ۳ تا ۵ هشتگ مرتبط به فارسی در انتهای متن اضافه کنید
5. اگر خبر مربوط به یک کشور خاص بود (مثلاً ایران، آمریکا، اسرائیل، چین، روسیه و...)، حتماً پرچم ایموجی آن کشور (مثلاً 🇮🇷 🇺🇸 🇮🇱 🇨🇳 🇷🇺) را در ابتدای عنوان خبر قرار دهید
6. از ایموجی در صورت نیاز و به‌جا استفاده کنید
7. فقط متن نهایی را برگردانید
8. خروجی را در قالب زیر بدهید (دقیقاً با همین تگ‌ها):

<TITLE>
عنوان خبر (یک جمله کوتاه و گیرا)
</TITLE>

<BODY>
متن اصلی خبر بازنویسی‌شده
</BODY>

<HASHTAGS>
#هشتگ1 #هشتگ2 #هشتگ3
</HASHTAGS>

متن خبر:
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
