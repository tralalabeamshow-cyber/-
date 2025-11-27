# main.py — ФУТБОЛ-АВТОПИЛОТ 2025 на Render + API-Football (мои 3 триггера)
import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from datetime import datetime
from flask import Flask
from threading import Thread

# --- КОНФИГУРАЦИЯ И ЗАЩИТА ---
TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("FOOTBALL_API_KEY")
# Сначала получаем MY_ID как строку
my_id_str = os.getenv("MY_TELEGRAM_ID")

# Проверка, что все ключи есть
if not all([TOKEN, my_id_str, API_KEY]):
    print("ОШИБКА: Установи BOT_TOKEN, MY_TELEGRAM_ID и FOOTBALL_API_KEY в переменных окружения!")
    exit()

# Теперь безопасно конвертируем MY_ID в число
try:
    MY_ID = int(my_id_str)
except ValueError:
    print("ОШИБКА: MY_TELEGRAM_ID должен быть корректным числом!")
    exit()

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
# -----------------------------

# --- FLASK KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): 
    return "Football autopilot 2025 alive"

def run_flask(): 
    # Используем порт, который предоставит Render
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 10000))
    
def keep_alive(): 
    # Запускаем Flask-сервер в отдельном потоке
    Thread(target=run_flask, daemon=True).start()
# ------------------------

# --- API-FOOTBALL ---
HEADERS = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}
LIVE_URL = "https://v3.football.api-sports.io/fixtures?live=all"

# Множество для хранения ID матчей, по которым уже было отправлено уведомление
sent_matches = set() 

async def get_live_matches():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(LIVE_URL, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Возвращаем список матчей. Защита от KeyError: 'response'
                    return data.get("response", []) 
        except: 
            # Игнорируем ошибки сети или таймауты
            pass
    return []

# --- ОСНОВНОЙ СКАНЕР (ТВОИ 3 ТРИГГЕРА) ---
async def live_scanner():
    # Цикл сканера работает, пока бот запущен
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
                    # Пропускаем матч, если сигнал уже был отправлен
                    if match_id in sent_matches: continue

                    home = teams["home"]["name"]
                    away = teams["away"]["name"]
                    # Используем 0, если счет None
                    score = f"{goals['home'] or 0}:{goals['away'] or 0}" 
                    minute = fixture["status"]["elapsed"] or 0

                    # Фильтр только топ-лиги
                    if not any(x in league for x in ["Premier League","La Liga","Bundesliga","Serie A","Ligue 1","Champions League","Europa League"]):
                        continue

                    signal = None
                    
                    # 1. ТРИГГЕР: 0:0 к 27-38 минуте -> ТБ 1.5
                    if 27 <= minute <= 38 and score == "0:0":
                        signal = f"🚨 ФУТБОЛ ТБ 1.5\n28–38′ | 0:0\n<b>{home}</b> – <b>{away}</b>\n{league}"
                        
                    # 2. ТРИГГЕР: 72+ минута при 1:0 или 0:1 -> ТБ 2.5
                    elif minute >= 72 and score in ["1:0", "0:1"]:
                        signal = f"🚨 ФУТБОЛ ТБ 2.5\n72+′ | {score}\n<b>{home}</b> – <b>{away}</b>\n{league}"
                        
                    # 3. ТРИГГЕР: 65+ минута при 1:1 -> ТБ 2.5
                    elif minute >= 65 and score == "1:1":
                        signal = f"🚨 ФУТБОЛ ТБ 2.5\n65+′ | 1:1\n<b>{home}</b> – <b>{away}</b>\n{league}"

                    if signal:
                        await bot.send_message(MY_ID, signal)
                        # Добавляем ID матча в set, чтобы не отправлять повторно
                        sent_matches.add(match_id)

                except: 
                    # Игнорируем ошибки парсинга отдельного матча
                    continue
        except: 
            # Игнорируем ошибки основного цикла
            pass
            
        await asyncio.sleep(35)  # Пауза между запросами
        
# --- КОМАНДЫ ДЛЯ ПОЛЬЗОВАТЕЛЯ ---
@dp.message(lambda m: m.text and m.text.lower() == "/start")
async def start(msg: types.Message):
    await msg.answer("🔥 Футбол-автопилот 2025 запущен!\nМои 3 железных триггера работают 24/7.")

@dp.message(lambda m: m.text and m.text.lower() == "/status")
async def status(msg: types.Message):
    await msg.answer(f"Бот живой\nАктивных триггеров (уведомлений отправлено): {len(sent_matches)}\nВремя: {datetime.now().strftime('%H:%M:%S')}")

# --- ЗАПУСК БОТА ---
async def on_startup():
    await bot.send_message(MY_ID, "🟢 ФУТБОЛ-АВТОПИЛОТ 2025 ЗАПУЩЕН И ГОТОВ К РАБОТЕ!")
    # Запускаем сканер в фоновом режиме
    asyncio.create_task(live_scanner())

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() # Запускаем Flask-сервер для Render
    asyncio.run(main())
