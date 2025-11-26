import asyncio
import aiohttp
import os
import json # Добавляем json для обработки ответа
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
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

# --- ВЕБ-СЕРВЕР ДЛЯ ОБХОДА "СНА" (RENDER) ---
RENDER_PORT = int(os.environ.get("PORT", 10000))
app = Flask('')

@app.route('/')
def home():
    return "Bot is running and awake! API testing mode."

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
        "💪 Бот запущен! Готовлюсь протестировать новый API: https://api.sstats.net. "
        "Используй команду /test_api."
    )

@dp.message(lambda message: message.text == '/test_api')
async def handle_api_test(message: types.Message):
    await message.answer("📡 Отправляю запрос на https://api.sstats.net...")
    
    # Твоя новая ссылка
    API_URL = "https://api.sstats.net"
    
    response_content = await get_api_response(API_URL)
    
    if response_content:
        # Обрезаем ответ, чтобы он не был слишком большим для Telegram
        content_preview = response_content[:800] 
        if len(response_content) > 800:
            content_preview += "..."

        await message.answer(
            f"<b>✅ Ответ от API (первые 800 символов):</b>\n\n"
            f"<code>{content_preview}</code>\n\n"
            f"<i>Общая длина ответа: {len(response_content)} символов.</i>",
            parse_mode="HTML"
        ) 
    else:
        await message.answer("😔 Ошибка: Не удалось получить ответ или API вернул пустые данные.")


# --- ФУНКЦИЯ ДЛЯ ТЕСТИРОВАНИЯ API ---
async def get_api_response(url):
    """Отправляет запрос GET на API и возвращает содержимое как текст."""
    async with aiohttp.ClientSession() as s: 
        try:
            async with s.get(url, timeout=10) as r:
                
                if r.status == 200:
                    # Возвращаем весь ответ как текст
                    return await r.text()
                else:
                    print(f"Ошибка HTTP: {r.status}")
                    return f"HTTP Error: {r.status}"
                    
        except Exception as e:
            print(f"Критическая ошибка при запросе: {e}")
            return None
        

# УБИРАЕМ все старые функции
async def get_matches_from_api(url): pass 
async def download_text_file(url): pass 
async def morning_tennis(): pass

async def on_startup():
    await bot.send_message(MY_ID, "ОБЩИЙ БОТ: РЕЖИМ ТЕСТИРОВАНИЯ API ЗАПУЩЕН.")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() 
    asyncio.run(main())
