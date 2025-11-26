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
TOKEN = os.getenv("BOT_TOKEN")
MY_ID = os.getenv("MY_TELEGRAM_ID")
# НОВЫЙ КЛЮЧ
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY") 

if not TOKEN or not MY_ID or not FOOTBALL_API_KEY:
    print("Ошибка: Установите BOT_TOKEN, MY_TELEGRAM_ID и FOOTBALL_API_KEY!")
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

# --- ВЕБ-СЕРВЕР ДЛЯ ОБХОДА "СНА" (RENDER) ---
RENDER_PORT = int(os.environ.get("PORT", 10000))
app = Flask('')

@app.route('/')
def home():
    return "Bot is running and awake! Professional API mode."

def run_flask_server():
  app.run(host='0.0.0.0', port=RENDER_PORT)

def keep_alive():
    t = Thread(target=run_flask_server)
    t.start()
# ---------------------------------------------


# 2. ФУНКЦИИ ДЛЯ РАБОТЫ С НОВЫМ API
async def get_raw(endpoint):
    """Отправляет запрос на внешний API с использованием ключа."""
    
    # Заголовки, необходимые для большинства профессиональных API
    headers = {
        'x-rapidapi-key': FOOTBALL_API_KEY, 
        'x-rapidapi-host': 'v3.football.api-sport.io' # Чаще всего используется этот хост
    }
    
    # URL для получения сегодняшних матчей (API-FOOTBALL)
    date_str = datetime.now().strftime('%Y-%m-%d')
    API_URL = f"https://v3.football.api-sport.io/fixtures?date={date_str}" 

    async with aiohttp.ClientSession(headers=headers) as s: 
        try:
            async with s.get(API_URL, timeout=15) as r:
                if r.status == 200:
                    data = await r.json()
                    # Проверяем, что API вернул успешный ответ
                    if 'response' in data:
                        return data['response']
                else:
                    print(f"Ошибка HTTP: {r.status}")
        except Exception as e:
            print(f"Критическая ошибка при запросе к API: {e}")
            
        return []

async def get_matches_for_display():
    """Форматирует данные о матчах для отправки пользователю."""
    raw_matches = await get_raw("/fixtures")
    
    if not raw_matches:
        return "😔 Сегодняшних матчей не найдено или API не вернул данные."

    # Фильтрация и форматирование (на основе структуры API-FOOTBALL)
    match_list = []
    for match in raw_matches[:10]: # Ограничимся 10 матчами для теста
        
        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        
        # Статус матча: 'Time to be defined', 'Not Started', 'Live', 'Match Finished'
        status = match['fixture']['status']['short']
        
        # Счет
        score_home = match['goals']['home'] if match['goals']['home'] is not None else '0'
        score_away = match['goals']['away'] if match['goals']['away'] is not None else '0'
        
        # Форматирование статуса
        if status == 'NS':
            time = datetime.fromtimestamp(match['fixture']['timestamp']).strftime('%H:%M')
            status_display = f"⏰ {time}"
        elif status in ('1H', 'HT', '2H', 'ET'):
            status_display = f"🟢 LIVE"
        elif status == 'FT':
            status_display = f"✅ FIN"
        else:
            status_display = f"[{status}]"
            
        match_list.append(f"{status_display} | <b>{home}</b> {score_home}-{score_away} <b>{away}</b>")

    if not match_list:
        return "😔 Сегодняшних топ-матчей, которые можно отобразить, не найдено."
        
    return "<b>⚽️ ФУТБОЛ СЕГОДНЯ (LIVE):</b>\n\n" + "\n".join(match_list)


# 3. ХЕНДЛЕРЫ КОМАНД 
@dp.message(lambda message: message.text == '/start')
async def handle_start(message: types.Message):
    await message.answer(
        "💪 Бот запущен! Используется **профессиональный API** для получения данных.\n"
        "Проверим матчи: /football"
    )

@dp.message(lambda message: message.text == '/football')
async def handle_football_today(message: types.Message):
    await message.answer("📡 Получаю данные о матчах...")
    
    text_to_send = await get_matches_for_display()
    
    await message.answer(text_to_send, disable_web_page_preview=True)

# 4. ЗАПУСК
async def on_startup():
    await bot.send_message(MY_ID, "ОБЩИЙ БОТ: ПРОФЕССИОНАЛЬНЫЙ API ЗАПУЩЕН.")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() 
    asyncio.run(main())
