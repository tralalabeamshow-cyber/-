import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties # <-- ИСПРАВЛЕНИЕ: НОВЫЙ ИМПОРТ
from datetime import datetime
from flask import Flask
from threading import Thread

# --- БЕЗОПАСНОЕ ПОЛУЧЕНИЕ ТОКЕНА И ID ---
TOKEN = os.getenv("BOT_TOKEN")
MY_ID = os.getenv("MY_TELEGRAM_ID") 

if not TOKEN or not MY_ID:
    print("Ошибка: Переменные BOT_TOKEN и MY_TELEGRAM_ID не установлены!")
    exit()

try:
    MY_ID = int(MY_ID)
except ValueError:
    print("Ошибка: MY_TELEGRAM_ID должен быть числом!")
    exit()
# ----------------------------------------

# 1. ОБЪЯВЛЕНИЕ БОТА И ДИСПЕТЧЕРА
# ИСПРАВЛЕНИЕ: Используем default=DefaultBotProperties для parse_mode
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# --- ФИЛЬТР ТОЛЬКО ДЛЯ ТЕБЯ (Опционально) ---
# Если хочешь, чтобы бот реагировал только на твой ID, раскомментируй эти строчки:
# class IsAdmin(types.base.TelegramObject):
#     async def check(self, obj: types.Message) -> bool:
#         return obj.from_user.id == MY_ID
# dp.message.filter(IsAdmin())
# dp.callback_query.filter(IsAdmin())
# ---------------------------------------------

HEADERS = {"x-fsign": "SW9D1eZo", "User-Agent": "Mozilla/5.0"}
sent_live = set()
morning_sent = False

# --- ВЕБ-СЕРВЕР ДЛЯ ОБХОДА "СНА" (RENDER) ---
RENDER_PORT = int(os.environ.get("PORT", 10000))
app = Flask('')

@app.route('/')
def home():
    return "Bot is running and awake!"

def run_flask_server():
  app.run(host='0.0.0.0', port=RENDER_PORT)

def keep_alive():
    t = Thread(target=run_flask_server)
    t.start()
# ---------------------------------------------


# 2. ХЕНДЛЕРЫ КОМАНД (Реагирует на /start)
@dp.message(lambda message: message.text == '/start')
async def handle_start(message: types.Message):
    """Отвечает пользователю, когда он пишет /start."""
    await message.answer(
        "💪 Бот-сканер запущен! Я буду отправлять все сигналы "
        "по футболу и теннису в этот чат. Если хочешь узнать о "
        "правилах сканирования, напиши /info."
    )


# --- ТВОИ АСИНХРОННЫЕ ФУНКЦИИ (ЛАЙВ-СКАНЕР) ---
async def get_raw(endpoint):
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        async with s.get(f"https://d.flashscore.com/x/feed/{endpoint}") as r:
            return await r.text() if r.status == 200 else ""

async def morning_tennis():
    global morning_sent
    while True:
        now = datetime.now()
        if now.hour == 10 and now.minute < 5 and not morning_sent:
            raw = await get_raw("tr_1")
            matches = []
            for line in raw.split("~"):
                if "AA" in line and ("challenger" in line.lower() or "itf" in line.lower()):
                    parts = line.split("¬")
                    p1 = next((p[4:] for p in parts if p.startswith("AD")), "?")
                    p2 = next((p[4:] for p in parts if p.startswith("AE")), "?")
                    tour = next((p[6:] for p in parts if p.startswith("AF")), "")
                    matches.append(f"• {p1} – {p2}\n   {tour}")
            if matches:
                text = f"<b>ТЕННИС НА СЕГОДНЯ ({now.strftime('%d.%m')})</b>\nНа что смотреть:\n\n" + "\n\n".join(matches[:15])
                await bot.send_message(MY_ID, text)
            morning_sent = True
        if now.hour == 0 and now.minute < 5:
            morning_sent = False
        await asyncio.sleep(60)

async def live_scanner():
    while True:
        try:
            data = await get_raw("tl_1")
            for line in data.split("~"):
                if "AA" not in line: continue
                parts = line.split("¬")
                mid = next((p[4:] for p in parts if p.startswith("AA")), None)
                if not mid or mid in sent_live: continue

                home = next((p[4:] for p in parts if p.startswith("AD")), "")
                away = next((p[4:] for p in parts if p.startswith("AE")), "")
                score = next((p[6:] for p in parts if p.startswith("AG")), "0:0")
                minute_str = next((p[6:] for p in parts if p.startswith("AC")), "0")
                league = next((p[6:] for p in parts if p.startswith("AF")), "")

                minute = int(''.join(filter(str.isdigit, minute_str)) or 0)

                # ФУТБОЛ
                if any(l in league for l in ["Premier","La Liga","Bundesliga","Serie A","Ligue 1","Champions","Europa"]):
                    if 27 <= minute <= 38 and score == "0:0":
                        await bot.send_message(MY_ID, f"ФУТБОЛ ТБ 1.5\n28–38′ | 0:0\n{home} – {away}\n{league}")
                        sent_live.add(mid)
                    if minute >= 72 and score in ["1:0","0:1"]:
                        await bot.send_message(MY_ID, f"ФУТБОЛ ТБ 2.5\n72+′ | {score}\n{home} – {away}\n{league}")
                        sent_live.add(mid)
                    if minute >= 65 and score == "1:1":
                        await bot.send_message(MY_ID, f"ФУТБОЛ ТБ 2.5\n65+′ | 1:1\n{home} – {away}\n{league}")

                # ТЕННИС
                if "challenger" in league.lower() or "itf" in league.lower():
                    if any(x in score for x in ["7:6","7:5","6:7","5:7"]):
                        await bot.send_message(MY_ID, f"ТЕННИС — тяжёлый сет!\n{home} – {away}\n{score}\nСтавь против уставшего!")
                        sent_live.add(mid)
                    if "1:0" in score and any(x in score.split()[-1] for x in ["4:0","4:1","5:1","5:2"]):
                        await bot.send_message(MY_ID, f"ТЕННИС — девушка сушит!\n{home} – {away}\n{score}")
                        sent_live.add(mid)
                    if "1:0" in score and any(x in score.split()[-1] for x in ["0:3","0:4","1:4","1:5"]):
                        await bot.send_message(MY_ID, f"ТЕННИС — ноги кончились!\n{home} – {away}\n{score}")
                        sent_live.add(mid)

        except: pass
        await asyncio.sleep(35)

async def on_startup():
    await bot.send_message(MY_ID, "ОБЩИЙ БОТ 2025 ЗАПУЩЕН!\nУтром — теннис на день\nДнём — мгновенные сигналы по футболу и теннису")
    asyncio.create_task(morning_tennis())
    asyncio.create_task(live_scanner())

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() # <-- Сначала запускаем веб-сервер
    asyncio.run(main()) # <-- Затем запускаем бота

