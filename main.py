# main.py — ФУТБОЛ-АВТОПИЛОТ 2025 (ФИНАЛЬНАЯ ВЕРСИЯ НОЯБРЬ 2025)
import asyncio
import aiohttp
import os
from datetime import datetime
from threading import Thread
from flask import Flask

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command

# ================= КОНФИГ И ЗАЩИТА =================
# Получаем переменные окружения как строки
TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("FOOTBALL_KEY")
MY_ID_STR = os.getenv("MY_TELEGRAM_ID")

# 1. Проверка наличия всех переменных
if not all([TOKEN, API_KEY, MY_ID_STR]):
    print("ОШИБКА: Не хватает переменных окружения! Проверь BOT_TOKEN, FOOTBALL_KEY, MY_TELEGRAM_ID")
    # Используем exit(1) для сигнализации об ошибке
    exit(1)

# 2. Безопасное преобразование MY_ID в число
try:
    MY_ID = int(MY_ID_STR)
except ValueError:
    print("ОШИБКА: MY_TELEGRAM_ID должен быть корректным числом!")
    exit(1)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ================= FLASK KEEP-ALIVE ДЛЯ RENDER =================
app = Flask(__name__)

@app.route('/')
def home():
    return "Футбол-Автопилот 2025 — alive & kicking ⚽️"

def run_flask():
    # Render предоставляет порт через переменную окружения
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    # Запуск Flask-сервера в отдельном потоке
    Thread(target=run_flask, daemon=True).start()

# ================= API-FOOTBALL =================
HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}
LIVE_URL = "https://v3.football.api-sports.io/fixtures?live=all"

sent_matches = set()   # ID матчей, по которым уже улетел сигнал

async def get_live_matches() -> list:
    """Выполняет запрос к API-Football и возвращает список LIVE матчей."""
    # Используем таймаут для предотвращения зависания
    async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=20)) as session:
        try:
            async with session.get(LIVE_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", [])
        except Exception as e:
            # Логируем ошибку API, но не прерываем работу бота
            print(f"Ошибка запроса к API-Football: {e}") 
    return []

# ================= ОСНОВНОЙ СКАНЕР (ТВОИ ТРИГГЕРЫ) =================
async def football_scanner():
    """Основной цикл сканера: проверяет матчи каждые 33 секунды."""
    while True:
        try:
            matches = await get_live_matches()
            for m in matches:
                try:
                    fid = m["fixture"]["id"]
                    if fid in sent_matches:
                        continue

                    home = m["teams"]["home"]["name"]
                    away = m["teams"]["away"]["name"]
                    # Используем 0, если счет None
                    score = f"{m['goals']['home'] or 0}:{m['goals']['away'] or 0}" 
                    minute = m["fixture"]["status"]["elapsed"] or 0
                    league = m["league"]["name"]

                    # Только топ-лиги
                    top_leagues = ["Premier League", "La Liga", "Bundesliga", "Serie A", 
                                 "Ligue 1", "Champions League", "Europa League", "Europa Conference League"]
                    
                    # ИСПРАВЛЕНИЕ: Исправлена опечатка 'league_name_name' на 'league_name'
                    if not any(league_name in league for league_name in top_leagues):
                        continue

                    signal = None

                    # Триггер 1: Ранний гол
                    if 27 <= minute <= 38 and score == "0:0":
                        signal = f"🚨 ТБ 1.5 (Триггер 1)\n27–38′ · 0:0\n<b>{home}</b> — <b>{away}</b>\n{league}"

                    # Триггер 2: Поздний гол при минимальном счете
                    elif minute >= 72 and score in ["1:0", "0:1"]:
                        signal = f"🚨 ТБ 2.5 (Триггер 2)\n72+′ · {score}\n<b>{home}</b> — <b>{away}</b>\n{league}"

                    # Триггер 3: Гол при ничьей
                    elif minute >= 65 and score == "1:1":
                        signal = f"🚨 ТБ 2.5 (Триггер 3)\n65+′ · 1:1\n<b>{home}</b> — <b>{away}</b>\n{league}"

                    if signal:
                        await bot.send_message(MY_ID, signal)
                        sent_matches.add(fid)
                        
                        # Чистим старые ID, чтобы память не росла бесконечно
                        if len(sent_matches) > 500:
                            sent_matches.clear()

                except Exception:
                    # Игнорируем ошибки в обработке одного матча
                    continue  
        except Exception as e:
            # Игнорируем глобальные ошибки сканера
            print(f"Критическая ошибка в сканере: {e}") 

        await asyncio.sleep(33)  # Пауза между итерациями

# ================= КОМАНДЫ =================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Отправляет приветственное сообщение и описание триггеров."""
    await message.answer(
        "⚽️ <b>ФУТБОЛ-АВТОПИЛОТ 2025</b> работает 24/7\n\n"
        "Активные триггеры:\n"
        "• 27–38′ + 0:0 → ТБ 1.5\n"
        "• 72+′ + 1:0 или 0:1 → ТБ 2.5\n"
        "• 65+′ + 1:1 → ТБ 2.5\n\n"
        "Сигналы приходят только тебе в ЛС 🔥"
    )

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    """Отправляет текущий статус бота."""
    api_status = await get_live_matches() # Пытаемся получить данные для пинга
    
    await message.answer(
        f"Статус: 🟢 онлайн\n"
        f"Сигналов отправлено за сессию: {len(sent_matches)}\n"
        f"Время сервера: {datetime.utcnow().strftime('%H:%M:%S UTC')}\n"
        f"Пинг API: {'✅ ок' if api_status is not None and api_status != [] else '❌ ошибка'}"
    )

# ================= ЗАПУСК =================
async def on_startup():
    """Вызывается при старте бота."""
    await bot.send_message(MY_ID, "🟢 ФУТБОЛ-АВТОПИЛОТ 2025 ЗАПУЩЕН И РАБОТАЕТ 24/7!")
    # Запускаем сканер в фоновом режиме
    asyncio.create_task(football_scanner())

async def main():
    """Основная функция для запуска aiogram."""
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()        # Запускаем Flask-сервер
    asyncio.run(main()) # Запускаем aiogram
