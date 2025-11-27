# main.py — ФУТБОЛ-АВТОПИЛОТ 2025 (полностью защищенный код для Render)
import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from datetime import datetime
from flask import Flask
from threading import Thread

# === КОНФИГУРАЦИЯ И КРИТИЧЕСКАЯ ЗАЩИТА ===
# Получаем переменные окружения как строки
TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("FOOTBALL_KEY")
my_id_str = os.getenv("MY_TELEGRAM_ID") # Получаем сначала как строку

# 1. Проверяем, что все строки существуют
if not all([TOKEN, API_KEY, my_id_str]):
    print("КРИТИЧЕСКАЯ ОШИБКА: Установите BOT_TOKEN, FOOTBALL_KEY и MY_TELEGRAM_ID в настройках Render!")
    exit()

# 2. Безопасно конвертируем MY_ID в число
try:
    MY_ID = int(my_id_str)
except ValueError:
    print("КРИТИЧЕСКАЯ ОШИБКА: MY_TELEGRAM_ID должен быть числом, а не текстом!")
    exit()
# ========================================

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Flask — чтобы Render не усыплял бота (Keep-Alive)
app = Flask(__name__)
@app.route('/')
def home():
    return "Футбол-бот работает 24/7!"

def keep_alive():
    # Запуск Flask-сервера в отдельном потоке, используя порт, предоставленный Render
    Thread(target=lambda: app.run(host='0.0.0.0', port=os.environ.get("PORT", 10000)), daemon=True).start()

# Уже отправленные матчи (чтобы не спамить)
sent_matches = set()

# Получаем только LIVE матчи
async def get_live_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    # Используем aiohttp.ClientSession для асинхронных запросов
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Защита от отсутствия ключа 'response'
                    return data.get("response", []) 
        except:
            # Игнорируем ошибки сети или таймауты, чтобы цикл сканера не прервался
            pass
    return []

# Главный сканер — мои 3 триггера
async def scanner():
    while True:
        try:
            matches = await get_live_matches()
            for match in matches:
                try:
                    # Основные данные матча
                    fid = match["fixture"]["id"]
                    if fid in sent_matches:
                        continue

                    home = match["teams"]["home"]["name"]
                    away = match["teams"]["away"]["name"]
                    # Используем 0, если счет None
                    score = f"{match['goals']['home'] or 0}:{match['goals']['away'] or 0}"
                    minute = match["fixture"]["status"]["elapsed"] or 0
                    league = match["league"]["name"]

                    # Фильтр: Только топ-лиги
                    if not any(l in league for l in ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1", "Champions League", "Europa League"]):
                        continue

                    # --- ЛОГИКА ТРИГГЕРОВ ---
                    signal = None
                    
                    # 1. ТРИГГЕР: 0:0 к 27-38 минуте -> ТБ 1.5
                    if 27 <= minute <= 38 and score == "0:0":
                        signal = f"🔥 ТБ 1.5 (Триггер 1)\n28–38 минута | 0:0\n<b>{home}</b> – <b>{away}</b>\n{league}"
                        
                    # 2. ТРИГГЕР: 72+ минута при 1:0 или 0:1 -> ТБ 2.5
                    elif minute >= 72 and score in ["1:0", "0:1"]:
                        signal = f"🔥 ТБ 2.5 (Триггер 2)\n72+ минута | {score}\n<b>{home}</b> – <b>{away}</b>\n{league}"
                        
                    # 3. ТРИГГЕР: 65+ минута при 1:1 -> ТБ 2.5
                    elif minute >= 65 and score == "1:1":
                        signal = f"🔥 ТБ 2.5 (Триггер 3)\n65+ минута | 1:1\n<b>{home}</b> – <b>{away}</b>\n{league}"

                    if signal:
                        await bot.send_message(MY_ID, signal)
                        sent_matches.add(fid)
                        if len(sent_matches) > 300:
                            sent_matches.clear()  # чистим set, чтобы не переполнять память

                except Exception as e:
                    # Если ошибка в одном матче (например, неверный ключ) — идем к следующему
                    continue 
        except Exception as e:
            # Если ошибка в основном цикле (например, сбой сети) — просто ждем и пробуем снова
            print(f"Ошибка в основном цикле сканера: {e}")
            
        await asyncio.sleep(35)  # Пауза между запросами к API

# Команда /start
@dp.message(lambda message: message.text and "start" in message.text.lower())
async def start(message: types.Message):
    await message.answer(
        "⚽️ **ФУТБОЛ-АВТОПИЛОТ 2025** запущен!\n"
        "Мои 3 железных триггера:\n"
        "• 27–38′ + 0:0 → ТБ 1.5\n"
        "• 72+′ + 1:0/0:1 → ТБ 2.5\n"
        "• 65+′ + 1:1 → ТБ 2.5\n\n"
        "Жди автоматических пушей – и удачи!"
    )

# Команда /status
@dp.message(lambda message: message.text and "status" in message.text.lower())
async def status(message: types.Message):
    await message.answer(f"Бот живой и сканирует.\nУведомлений отправлено за сессию: {len(sent_matches)}\nВремя (UTC): {datetime.utcnow().strftime('%H:%M:%S')}")

# --- ЗАПУСК БОТА ---
async def on_startup():
    await bot.send_message(MY_ID, "🟢 ФУТБОЛ-АВТОПИЛОТ 2025 ВКЛЮЧЁН! Сканер запущен 24/7.")
    # Запускаем сканер в фоновом режиме
    asyncio.create_task(scanner()) 

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

# === ТОЧКА ВХОДА ===
if __name__ == "__main__":
    keep_alive()        # Запускаем Flask-сервер
    asyncio.run(main()) # Запускаем бота
