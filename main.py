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
        "💪 Бот-сканер запущен! Главная задача: проверить соединение с интернетом командой /test_connection"
    )

@dp.message(lambda message: message.text == '/test_connection')
async def handle_connection_test(message: types.Message):
    await message.answer("📡 Проверяю подключение к Google...")
    
    test_result = await test_internet_connection()
    
    await message.answer(test_result) 

@dp.message(lambda message: message.text == '/football')
async def handle_football_today(message: types.Message):
    await message.answer("⚠️ Сначала проверь, может ли бот вообще выйти в интернет, используя команду /test_connection.")
    

# --- ДИАГНОСТИЧЕСКАЯ ФУНКЦИЯ ---
async def test_internet_connection():
    """Проверяет, может ли бот сделать внешний HTTP-запрос."""
    url = "https://www.google.com" # Пробуем подключиться к Google
    
    try:
        async with aiohttp.ClientSession() as s: 
            # Установили таймаут 10 секунд
            async with s.get(url, timeout=10) as r: 
                
                if r.status == 200:
                    return f"✅ УСПЕХ: Соединение установлено. Код ответа: {r.status}."
                else:
                    return f"❌ ОШИБКА: Соединение установлено, но код ответа: {r.status}."
                    
    except aiohttp.ClientConnectorError:
        return "❌ ОШИБКА: Не удалось установить соединение (ClientConnectorError)."
    except asyncio.TimeoutError:
        return "❌ ОШИБКА: Превышено время ожидания (TimeoutError)."
    except Exception as e:
        return f"❌ НЕИЗВЕСТНАЯ ОШИБКА: {type(e).__name__} - {e}"
        

# УБИРАЕМ все старые функции
async def get_matches_from_api(url): pass
async def get_raw(endpoint): pass 
async def morning_tennis(): pass

async def on_startup():
    await bot.send_message(MY_ID, "ОБЩИЙ БОТ: ТЕСТ СОЕДИНЕНИЯ ЗАПУЩЕН.")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() 
    asyncio.run(main())
