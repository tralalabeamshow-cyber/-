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
    return "Bot is running and awake! FINAL DIAGNOSTIC MODE."

def run_flask_server():
  app.run(host='0.0.0.0', port=RENDER_PORT)

def keep_alive():
    t = Thread(target=run_flask_server)
    t.start()
# ---------------------------------------------


# 2. ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ СЫРЫХ ДАННЫХ
async def get_raw_data():
    """Отправляет запрос на твой API с использованием ключа и возвращает текст ответа."""
    
    # ******* ИЗМЕНИ ЭТИ ДВЕ ЧАСТИ ПОД СВОЙ API *******
    API_URL = "https://v3.football.api-sport.io/fixtures?date=" + datetime.now().strftime('%Y-%m-%d')
    HEADERS = {
        'x-rapidapi-key': FOOTBALL_API_KEY, 
        'x-rapidapi-host': 'v3.football.api-sport.io' # ИЛИ ТВОЙ ХОСТ
    }
    # **********************************************

    async with aiohttp.ClientSession(headers=HEADERS) as s: 
        try:
            async with s.get(API_URL, timeout=15) as r:
                if r.status == 200:
                    # Важно: возвращаем весь текст ответа, чтобы увидеть структуру
                    return await r.text() 
                else:
                    return f"HTTP Error: {r.status} - {await r.text()}"
        except Exception as e:
            return f"Критическая ошибка при запросе к API: {e}"
            
        return "Неизвестная ошибка."

# 3. ХЕНДЛЕРЫ КОМАНД 
@dp.message(lambda message: message.text == '/start')
async def handle_start(message: types.Message):
    await message.answer(
        "💪 Бот запущен! Готовлюсь к ФИНАЛЬНОЙ ДИАГНОСТИКЕ.\n"
        "Запустите /get_raw_data."
    )

@dp.message(lambda message: message.text == '/get_raw_data')
async def handle_football_today(message: types.Message):
    await message.answer("📡 Получаю сырые данные от API...")
    
    raw_data = await get_raw_data()
    
    # Обрезаем ответ, чтобы он не был слишком большим для Telegram
    content_preview = raw_data[:1000] 
    if len(raw_data) > 1000:
        content_preview += "\n\n... (ответ обрезан)"

    await message.answer(
        f"<b>✅ Сырой Ответ от API:</b>\n\n"
        f"<code>{content_preview}</code>",
        parse_mode="HTML"
    )
# ... (остальные функции не важны для диагностики)
# 4. ЗАПУСК (Оставить без изменений)
async def on_startup():
    await bot.send_message(MY_ID, "ОБЩИЙ БОТ: РЕЖИМ СЫРОЙ ДИАГНОСТИКИ ЗАПУЩЕН.")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() 
    asyncio.run(main())
