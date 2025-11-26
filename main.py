import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from datetime import datetime, timedelta # <-- ИСПРАВЛЕНИЕ: ДОБАВЛЕН timedelta
from flask import Flask
from threading import Thread

# --- БЕЗОПАСНОЕ ПОЛУЧЕНИЕ ТОКЕНА И ID ---
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

HEADERS = {"x-fsign": "SNQ_wNYt", "User-Agent": "Mozilla/5.0"}
sent_live = set()
morning_sent = False




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


# 2. ХЕНДЛЕРЫ КОМАНД (Реагируют на команды)
@dp.message(lambda message: message.text == '/start')
async def handle_start(message: types.Message):
    """Отвечает пользователю, когда он пишет /start."""
    await message.answer(
        "💪 Бот-сканер запущен! Я буду отправлять все сигналы "
        "по футболу и теннису в этот чат. Если хочешь узнать о "
        "правилах сканирования, напиши /info."
    )

@dp.message(lambda message: message.text == '/tennis')
async def handle_tennis_today(message: types.Message):
    """
    Запускает функцию сканирования тенниса на сегодня по требованию.
    """
    await message.answer("🎾 Ищу челленджеры и ITF на сегодня... Подождите 5-10 секунд.")
    
    raw = await get_raw("tr_1") # tr_1 - сегодняшний теннис
    matches = []
    
    for line in raw.split("~"):
        if "AA" in line and ("challenger" in line.lower() or "itf" in line.lower()):
            parts = line.split("¬")
            p1 = next((p[4:] for p in parts if p.startswith("AD")), "?")
            p2 = next((p[4:] for p in parts if p.startswith("AE")), "?")
            tour = next((p[6:] for p in parts if p.startswith("AF")), "")
            matches.append(f"• {p1} – {p2}\n   {tour}")

    now = datetime.now()
    if matches:
        text = f"<b>🎾 ТЕННИС НА СЕГОДНЯ ({now.strftime('%d.%m')})</b>\nНа что смотреть:\n\n" + "\n\n".join(matches[:15])
        await message.answer(text) 
    else:
        await message.answer("😔 На сегодня челленджеров/ITF в расписании не найдено.")


@dp.message(lambda message: message.text == '/upcoming')
async def handle_upcoming_matches(message: types.Message):
    """
    Ищет топ-матчи на 6 дней вперед.
    """
    await message.answer("🗓️ Ищу матчи на ближайшие 6 дней по футболу (топ-лиги) и теннису (челленджеры/ITF)... Это займет около 30 секунд.")
    
    all_future_matches = []
    major_leagues = ["Premier", "La Liga", "Bundesliga", "Serie A", "Ligue 1", "Champions", "Europa"]
    
    # Итерация с 1 по 6 день (завтра и далее)
    for day_offset in range(1, 7):
        date_obj = datetime.now() + timedelta(days=day_offset)
        date_str = date_obj.strftime('%d.%m')
        
        # ----------------------------------------------------
        # TENNIS (tr_1/D)
        # ----------------------------------------------------
        raw_tennis = await get_raw(f"tr_1/{day_offset}") # tr_1/1 = завтра, tr_1/6 = через 6 дней
        tennis_matches = []
        for line in raw_tennis.split("~"):
            if "AA" in line and ("challenger" in line.lower() or "itf" in line.lower()):
                parts = line.split("¬")
                p1 = next((p[4:] for p in parts if p.startswith("AD")), "?")
                p2 = next((p[4:] for p in parts if p.startswith("AE")), "?")
                tour = next((p[6:] for p in parts if p.startswith("AF")), "")
                tennis_matches.append(f"• 🎾 {p1} – {p2} ({tour})")

        # ----------------------------------------------------
        # FOOTBALL (fa_1/D)
        # ----------------------------------------------------
        raw_football = await get_raw(f"fa_1/{day_offset}") # fa_1/1 = завтра, fa_1/6 = через 6 дней
        football_matches = []
        
        for line in raw_football.split("~"):
            if "AA" in line:
                parts = line.split("¬")
                league = next((p[6:] for p in parts if p.startswith("AF")), "")
                
                if any(l in league for l in major_leagues):
                    home = next((p[4:] for p in parts if p.startswith("AD")), "")
                    away = next((p[4:] for p in parts if p.startswith("AE")), "")
                    time_raw = next((p[6:] for p in parts if p.startswith("AH")), "")
                    # Используем try/except, чтобы избежать падений, если время не указано
                    try:
                        time_str = datetime.fromtimestamp(int(time_raw)).strftime('%H:%M')
                    except:
                        time_str = '??:??'
                    
                    football_matches.append(f"• ⚽ {time_str} | {home} – {away} ({league})")

        
        # Собираем результат за текущий день
        if tennis_matches or football_matches:
            day_text = f"📅 <b>{date_str}</b>:\n\n"
            if tennis_matches:
                day_text += "🎾 **Теннис (Челленджеры/ITF)**\n" + "\n".join(tennis_matches[:10]) + "\n\n"
            if football_matches:
                day_text += "⚽ **Футбол (Топ-Лиги)**\n" + "\n".join(football_matches[:10]) + "\n\n"
            
            all_future_matches.append(day_text)
            
    # Отправляем итоговое сообщение
    if all_future_matches:
        final_text = "".join(all_future_matches)
        await message.answer(final_text)
    else:
        await message.answer("😴 На ближайшие 6 дней подходящих топ-матчей не найдено.")


# --- ТВОИ АСИНХРОННЫЕ ФУНКЦИИ (ЛАЙВ-СКАНЕР И ГЛАВНАЯ ЛОГИКА) ---
async def get_raw(endpoint):
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        # Упрощаем, теперь endpoint может быть "tr_1" или "tr_1/1" и т.д.
        async with s.get(f"https://d.flashscore.com/x/feed/{endpoint}") as r: 
            return await r.text() if r.status == 200 else ""

async def morning_tennis():
    global morning_sent
    while True:
        now = datetime.now()
        if now.hour == 10 and now.minute < 5 and not morning_sent:
            # Логика для отправки утреннего сообщения в MY_ID (дублирует логику /tennis)
            raw = await get_raw("tr_1")
            matches = []
            for line in raw.split("~"):
                if "AA" in line and ("challenger" in line.lower() or "itf" in line.lower()):
                    parts = line.split("¬")
                    p1 = next((p[4:] for p in parts if p.startswith("AD")), "?")
                    p2 = next((p[4:] for p in parts if p.startswith("AE")), "?")
                    tour = next((p[6:] for p in parts if p.startswith("AF")), "")
                    matches.append(f"• {p1} – {p2}\n   {tour}")
            if matches:
                text = f"<b>ТЕННИС НА СЕГОДНЯ ({now.strftime('%d.%m')})</b>\nНа что смотреть:\n\n" + "\n\n".join(matches[:15])
                await bot.send_message(MY_ID, text)
            morning_sent = True
        if now.hour == 0 and now.minute < 5:
            morning_sent = False
        await asyncio.sleep(60)

async def live_scanner():
    while True:
        try:
            data = await get_raw("tl_1") # tl_1 - Live
            # ... (твой код live_scanner, без изменений)
            for line in data.split("~"):
                if "AA" not in line: continue
                parts = line.split("¬")
                mid = next((p[4:] for p in parts if p.startswith("AA")), None)
                if not mid or mid in sent_live: continue

                home = next((p[4:] for p in parts if p.startswith("AD")), "")
                away = next((p[4:] for p in parts if p.startswith("AE")), "")
                score = next((p[6:] for p in parts if p.startswith("AG")), "0:0")
                minute_str = next((p[6:] for p in parts if p.startswith("AC")), "0")
                league = next((p[6:] for p in parts if p.startswith("AF")), "")

                minute = int(''.join(filter(str.isdigit, minute_str)) or 0)

                # ФУТБОЛ
                if any(l in league for l in ["Premier","La Liga","Bundesliga","Serie A","Ligue 1","Champions","Europa"]):
                    if 27 <= minute <= 38 and score == "0:0":
                        await bot.send_message(MY_ID, f"ФУТБОЛ ТБ 1.5\n28–38′ | 0:0\n{home} – {away}\n{league}")
                        sent_live.add(mid)
                    if minute >= 72 and score in ["1:0","0:1"]:
                        await bot.send_message(MY_ID, f"ФУТБОЛ ТБ 2.5\n72+′ | {score}\n{home} – {away}\n{league}")
                        sent_live.add(mid)
                    if minute >= 65 and score == "1:1":
                        await bot.send_message(MY_ID, f"ФУТБОЛ ТБ 2.5\n65+′ | 1:1\n{home} – {away}\n{league}")

                # ТЕННИС
                if "challenger" in league.lower() or "itf" in league.lower():
                    if any(x in score for x in ["7:6","7:5","6:7","5:7"]):
                        await bot.send_message(MY_ID, f"ТЕННИС — тяжёлый сет!\n{home} – {away}\n{score}\nСтавь против уставшего!")
                        sent_live.add(mid)
                    if "1:0" in score and any(x in score.split()[-1] for x in ["4:0","4:1","5:1","5:2"]):
                        await bot.send_message(MY_ID, f"ТЕННИС — девушка сушит!\n{home} – {away}\n{score}")
                        sent_live.add(mid)
                    if "1:0" in score and any(x in score.split()[-1] for x in ["0:3","0:4","1:4","1:5"]):
                        await bot.send_message(MY_ID, f"ТЕННИС — ноги кончились!\n{home} – {away}\n{score}")
                        sent_live.add(mid)

        except: pass
        await asyncio.sleep(35)

async def on_startup():
    await bot.send_message(MY_ID, "ОБЩИЙ БОТ 2025 ЗАПУЩЕН!\nУтром — теннис на день\nДнём — мгновенные сигналы по футболу и теннису")
    asyncio.create_task(morning_tennis())
    asyncio.create_task(live_scanner())

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive() # <-- Сначала запускаем веб-сервер
    asyncio.run(main()) # <-- Затем запускаем бота
