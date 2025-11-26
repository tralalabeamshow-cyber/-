import asyncio
import aiohttp
import os
import json 
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from datetime import datetime
from flask import Flask
from threading import Thread

# --- КОНФИГУРАЦИЯ ---
# Переменные окружения должны быть установлены на Render:
# BOT_TOKEN, MY_TELEGRAM_ID, FOOTBALL_API_KEY
# --------------------

TOKEN = os.getenv("BOT_TOKEN")
MY_ID = os.getenv("MY_TELEGRAM_ID")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY") 

if not TOKEN or not MY_ID or not FOOTBALL_API_KEY:
    # Если ключи не найдены, печатаем ошибку и выходим
    print("Ошибка: Установите BOT_TOKEN, MY_TELEGRAM_ID и FOOTBALL_API_KEY в переменных окружения Render!")
    exit()

try:
    MY_ID = int(MY_ID)
except ValueError:
    print("Ошибка: MY_TELEGRAM_ID должен быть числом!")
    exit()

# 1. ОБЪЯВЛЕНИЕ БОТА И ДИСПЕТЧЕРА
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# --- ВЕБ-СЕРВЕР ДЛЯ ОБХОДА "СНА" (RENDER) ---
RENDER_PORT = int(os.environ.get("PORT", 10000))
app = Flask('')

@app.route('/')
def home():
    return "Bot is running and awake! Football service operational."

def run_flask_server():
  app.run(host='0.0.0.0', port=RENDER_PORT)

def keep_alive():
    t = Thread(target=run_flask_server)
    t.start()
# ---------------------------------------------


# 2. ФУНКЦИИ ДЛЯ РАБОТЫ С API-FOOTBALL
async def get_raw():
    """Отправляет запрос на API-FOOTBALL и возвращает массив матчей."""
    
    # Заголовки API-FOOTBALL
    headers = {
        'x-rapidapi-key': FOOTBALL_API_KEY, 
        'x-rapidapi-host': 'v3.football.api-sport.io'
    }
    
    # URL для получения сегодняшних матчей
    date_str = datetime.now().strftime('%Y-%m-%d')
    API_URL = f"https://v3.football.api-sport.io/fixtures?date={date_str}" 

    async with aiohttp.ClientSession(headers=headers) as s: 
        try:
            async with s.get(API_URL, timeout=15) as r:
                if r.status == 200:
                    data = await r.json()
                    # ИСПРАВЛЕНИЕ ЗАЩИТЫ: Проверяем наличие 'response' и его содержимое
                    if 'response' in data and isinstance(data['response'], list):
                        return data['response']
                    
                    # Если 'response' нет или оно не является списком, логируем ошибку API
                    print(f"API Error (No response list): {data.get('errors', 'Unknown API Error')}")
                    return []
                else:
                    print(f"Ошибка HTTP: {r.status}")
        except Exception as e:
            print(f"Критическая ошибка при запросе к API: {e}")
            
        return []

async def get_matches_for_display():
    """Форматирует данные о матчах для отправки пользователю."""
    raw_matches = await get_raw() # Получаем только массив матчей
    
    if not raw_matches:
        # Это сообщение будет отправлено, если API вернул 0 матчей или была ошибка в API
        return "😔 Сегодняшних матчей не найдено или превышен лимит API."

    match_list = []
    
    for match in raw_matches[:15]: # Ограничиваемся первыми 15 матчами
        try:
            # Парсинг данных (теперь он безопасен, так как мы знаем структуру)
            home = match['teams']['home']['name']
            away = match['teams']['away']['name']
            status = match['fixture']['status']['short']
            
            # Защита от None, если счет еще не начался
            score_home = match['goals']['home'] if match['goals']['home'] is not None else '0'
            score_away = match['goals']['away'] if match['goals']['away'] is not None else '0'
            
            # Форматирование статуса
            if status == 'NS': # Not Started
                time = datetime.fromtimestamp(match['fixture']['timestamp']).strftime('%H:%M')
                status_display = f"⏰ {time}"
            elif status in ('1H', 'HT', '2H', 'ET', 'P', 'BT'): # Live statuses
                status_display = f"🟢 LIVE"
            elif status == 'FT': # Finished
                status_display = f"✅ FIN"
            else:
                status_display = f"[{status}]"
                
            league_name = match['league']['name']
            
            match_list.append(f"({league_name}) {status_display} | <b>{home}</b> {score_home}-{score_away} <b>{away}</b>")

        except KeyError as e:
            # Логируем ошибку, но продолжаем, чтобы не падать из-за одного матча с плохими данными
            print(f"Ошибка парсинга одного матча: Missing key {e}")
            continue

    if not match_list:
        return "😔 Не удалось получить матчи, хотя API ответил (проблема парсинга)."
        
    return "<b>⚽️ ФУТБОЛ СЕГОДНЯ:</b>\n\n" + "\n".join(match_list)


# 3. ХЕНДЛЕРЫ КОМАНД 
@dp.message(lambda message: message.text == '/start')
async def handle_start(message: types.Message):
    await message.answer(
        "💪 Бот запущен! Используется **API-FOOTBALL**.\n"
        "Проверим матчи: /football"
    )

@dp.message(lambda message: message.text == '/football')
async def handle_football_today(message: types.Message):
    await message.answer("📡 Получаю данные о матчах...")
    
    text_to_send = await get_matches_for_display()
    
    await message.answer(text_to_send, disable_web_page_preview=True)

# 4. ЗАПУСК
async def on_startup():
    await bot.send_message(MY_ID, "ОБЩИЙ БОТ: API-FOOTBALL ЗАПУЩЕН.")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() 
    asyncio.run(main())
