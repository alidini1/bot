"""
نقطه ورود ربات
"""
import asyncio
from telegram_bot import NewsBot


async def main():
    bot = NewsBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n🛑 دریافت سیگنال توقف...")
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
