import asyncio
import aiohttp
import os
import json 
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# --- КЛЮЧИ И ID ---
TOKEN = os.getenv("BOT_TOKEN")
MY_ID = os.getenv("MY_TELEGRAM_ID") 
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY") 

if not TOKEN or not MY_ID or not SPORTS_API_KEY:
    print("Ошибка: Не установлены BOT_TOKEN, MY_TELEGRAM_ID или SPORTS_API_KEY!")
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

# НОВЫЕ ЗАГОЛОВКИ ДЛЯ API-FOOTBALL/RAPIDAPI
# Убедись, что host соответствует тому, что RapidAPI тебе дал!
HEADERS = {
    "x-rapidapi-key": SPORTS_API_KEY,
    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
}
# ... (остальной код инициализации без изменений)
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
        "💪 Бот-сканер запущен! Теперь я использую стабильный Sports API "
        "для поиска **футбольных** матчей. Теннис пока отключен. "
    )

@dp.message(lambda message: message.text == '/football')
async def handle_football_today(message: types.Message):
    await message.answer("⚽ Ищу топ-лиги на сегодня... Подождите 5-10 секунд.")
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # 1. API запрос - ИСПОЛЬЗУЕМ ТОЛЬКО URL ДЛЯ FIXTURES
    API_URL = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?date={date_str}" 
    
    matches = await get_matches_from_api(API_URL)
    
    if matches:
        text = f"<b>⚽ ФУТБОЛ НА СЕГОДНЯ ({datetime.now().strftime('%d.%m')})</b>\n\n" + "\n\n".join(matches)
        await message.answer(text) 
    else:
        # Теперь выводим более детальное сообщение
        await message.answer("😔 На сегодня топ-матчей не найдено.\nЕсли матчи есть, проверьте, пожалуйста, правильность **КЛЮЧА API**.")


# --- НОВЫЕ АСИНХРОННЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С JSON ---
async def get_matches_from_api(url):
    """Получает и парсит данные в формате JSON."""
    # ID ТОП-ЛИГ: 39-АПЛ, 140-ЛаЛига, 61-Лига 1, 78-Бундеслига, 135-Серия А.
    major_leagues = [39, 140, 61, 78, 135]
    
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        async with s.get(url) as r:
            
            if r.status != 200:
                print(f"Ошибка API: {r.status} - {await r.text()}")
                return []
            
            try:
                data = await r.json()
            except json.JSONDecodeError:
                print("Ошибка: API вернул невалидный JSON.")
                return []
            
            if 'response' not in data:
                return []
                
            matches = []
            
            for fixture in data['response']:
                league_id = fixture['league']['id']
                
                if league_id in major_leagues:
                    home = fixture['teams']['home']['name']
                    away = fixture['teams']['away']['name']
                    league_name = fixture['league']['name']
                    time_raw = fixture['fixture']['timestamp']
                    
                    time_str = datetime.fromtimestamp(time_raw).strftime('%H:%M')
                    
                    matches.append(f"• ⚽ {time_str} | {home} – {away} ({league_name})")
                    
            return matches

# УБИРАЕМ все старые функции, связанные с Flashscore
async def get_raw(endpoint): pass 
async def morning_tennis(): pass

async def on_startup():
    await bot.send_message(MY_ID, "ОБЩИЙ БОТ 2025 ПЕРЕКЛЮЧЕН НА SPORTS API.")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() 
    asyncio.run(main())
