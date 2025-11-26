import asyncio
import aiohttp
import os
import json 
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from datetime import datetime
from flask import Flask
from threading import Thread

# --- КЛЮЧИ И ID ---
# Для TheSportsDB ключ не нужен, используем "1" для публичного доступа
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
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# TheSportsDB: НЕ ТРЕБУЕТ ЗАГОЛОВКОВ ИЛИ КЛЮЧА
# Мы используем публичный ключ "1"
# HEADERS = {} # Убираем заголовки

sent_live = set()

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


# 2. ХЕНДЛЕРЫ КОМАНД 
@dp.message(lambda message: message.text == '/start')
async def handle_start(message: types.Message):
    await message.answer(
        "💪 Бот-сканер запущен! Используется **TheSportsDB** (без ключа). "
        "Проверим футбол командой /football."
    )

@dp.message(lambda message: message.text == '/football')
async def handle_football_today(message: types.Message):
    await message.answer("⚽ Ищу матчи на сегодня... Подождите 5-10 секунд.")
    
    # Дата в формате YYYY-MM-DD
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # API запрос для TheSportsDB: https://www.thesportsdb.com/api/v1/json/1/eventsday.php?d=2025-11-26
    API_URL = f"https://www.thesportsdb.com/api/v1/json/1/eventsday.php?d={date_str}" 
    
    matches = await get_matches_from_api(API_URL)
    
    if matches:
        text = f"<b>⚽ ФУТБОЛ НА СЕГОДНЯ ({datetime.now().strftime('%d.%m')})</b>\n\n" + "\n\n".join(matches)
        await message.answer(text) 
    else:
        await message.answer("😔 На сегодня матчей не найдено.\n(Если матчи есть, возможно, проблема в API-ссылке).")


# --- НОВЫЕ АСИНХРОННЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С JSON ---
async def get_matches_from_api(url):
    """Получает и парсит данные в формате JSON из TheSportsDB."""
    # TheSportsDB дает матчи по всем видам спорта, нам нужен только футбол.
    football_events = []
    
    # Заголовки не нужны
    async with aiohttp.ClientSession() as s: 
        async with s.get(url) as r:
            
            if r.status != 200:
                print(f"Ошибка API: {r.status} - {await r.text()}")
                return []
            
            try:
                data = await r.json()
            except json.JSONDecodeError:
                print("Ошибка: API вернул невалидный JSON.")
                return []
            
            # Проверяем, что в ответе есть события
            if 'events' not in data or data['events'] is None:
                return []
                
            for event in data['events']:
                # Фильтруем по футболу (Soccer)
                if event.get('strSport') == 'Soccer': 
                    
                    home = event.get('strHomeTeam', '?')
                    away = event.get('strAwayTeam', '?')
                    league_name = event.get('strLeague', '?')
                    time_str = event.get('strTime', '??:??')
                    
                    # Фильтруем, чтобы не брать совсем уж мелкие лиги
                    if "League" in league_name or "Cup" in league_name: 
                        football_events.append(f"• ⚽ {time_str} | {home} – {away} ({league_name})")
                    
            return football_events

# УБИРАЕМ все старые функции
async def get_raw(endpoint): pass 
async def morning_tennis(): pass

async def on_startup():
    await bot.send_message(MY_ID, "ОБЩИЙ БОТ: ПЕРЕХОД НА SPORTSDB.")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() 
    asyncio.run(main())
