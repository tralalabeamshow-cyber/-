# main.py — ФУТБОЛ-АВТОПИЛОТ 2025 на Render + API-Football (мои 3 триггера)
import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from datetime import datetime
from flask import Flask
from threading import Thread

# --- КОНФИГ ---
TOKEN = os.getenv("BOT_TOKEN")
MY_ID = int(os.getenv("MY_TELEGRAM_ID"))
API_KEY = os.getenv("FOOTBALL_API_KEY")

if not all([TOKEN, MY_ID, API_KEY]):
    print("ОШИБКА: Установи BOT_TOKEN, MY_TELEGRAM_ID и FOOTBALL_API_KEY в переменных окружения!")
    exit()

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Flask keep-alive
app = Flask('')
@app.route('/')
def home(): return "Football autopilot 2025 alive"

def run_flask(): app.run(host='0.0.0.0', port=os.environ.get("PORT", 10000))
def keep_alive(): Thread(target=run_flask, daemon=True).start()

# --- API-FOOTBALL ---
HEADERS = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}
LIVE_URL = "https://v3.football.api-sports.io/fixtures?live=all"

sent_matches = set()  # чтобы не спамить один и тот же матч

async def get_live_matches():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(LIVE_URL, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", [])
        except: pass
    return []

# --- ОСНОВНОЙ СКАНЕР (мои 3 триггера) ---
async def live_scanner():
    while True:
        try:
            matches = await get_live_matches()
            for m in matches:
                try:
                    fixture = m["fixture"]
                    teams = m["teams"]
                    goals = m["goals"]
                    league = m["league"]["name"]

                    match_id = fixture["id"]
                    if match_id in sent_matches: continue

                    home = teams["home"]["name"]
                    away = teams["away"]["name"]
                    score = f"{goals['home'] or 0}:{goals['away'] or 0}"
                    minute = fixture["status"]["elapsed"] or 0

                    # Фильтр только топ-лиги
                    if not any(x in league for x in ["Premier League","La Liga","Bundesliga","Serie A","Ligue 1","Champions League","Europa League"]):
                        continue

                    signal = None
                    if 27 <= minute <= 38 and score == "0:0":
                        signal = f"ФУТБОЛ ТБ 1.5\n28–38′ | 0:0\n{home} – {away}\n{league}"
                    elif minute >= 72 and score in ["1:0", "0:1"]:
                        signal = f"ФУТБОЛ ТБ 2.5\n72+′ | {score}\n{home} – {away}\n{league}"
                    elif minute >= 65 and score == "1:1":
                        signal = f"ФУТБОЛ ТБ 2.5\n65+′ | 1:1\n{home} – {away}\n{league}"

                    if signal:
                        await bot.send_message(MY_ID, signal)
                        sent_matches.add(match_id)

                except: continue
        except: pass
        await asyncio.sleep(35)  # каждые 35 сек

# --- КОМАНДЫ ---
@dp.message(lambda m: m.text and m.text.lower() == "/start")
async def start(msg: types.Message):
    await msg.answer("Футбол-автопилот 2025 запущен!\nМои 3 железных триггера работают 24/7")

@dp.message(lambda m: m.text and m.text.lower() == "/status")
async def status(msg: types.Message):
    await msg.answer(f"Бот живой\nАктивных триггеров: {len(sent_matches)}\nВремя: {datetime.now().strftime('%H:%M')}")

# --- ЗАПУСК ---
async def on_startup():
    await bot.send_message(MY_ID, "ФУТБОЛ-АВТОПИЛОТ 2025 ЗАПУЩЕН!\nТриггеры: 27–38′ 0:0 → ТБ 1.5\n72+′ 1:0/0:1 → ТБ 2.5\n65+′ 1:1 → ТБ 2.5")
    asyncio.create_task(live_scanner())

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())
