
# bot3.py — повний робочий код
import asyncio
import json
import datetime
import random
import time
from typing import Dict, Any
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

# ========== НАЛАШТУВАННЯ ==========
# API_TOKEN = "7571579058:AAHgxf2lrxSFVGQUt5Dx9b-PdomNzBxED9Y"  # <--- постав свій токен

import os
API_TOKEN = os.getenv("BOT_TOKEN")
AUTHOR_ID = 1365276193       # <--- свій Telegram ID (адмін/автор)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ========== УТИЛІТИ ==========
def load_json(filename: str, default=None):
    """
    Безпечне читання JSON. Якщо default не передано — повертаємо порожній dict.
    Якщо файл відсутній — створимо його з default-значенням.
    """
    if default is None:
        default = {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # створимо файл з дефолтом і повернемо його
        try:
            save_json(filename, default)
        except Exception:
            pass
        return default
    except Exception:
        return default


def save_json(filename: str, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def uid_str_from_message(msg: types.Message) -> str:
    return str(msg.from_user.id)

def display_name_from_item(item: Dict[str, Any]) -> str:
    if item.get("from_username"):
        return f"@{item.get('from_username')}"
    return str(item.get("from_id"))

def now_str():
    return str(datetime.datetime.now())

# ========== Дані ==========
schedule_data = load_json("schedule.json", {})
news_data = load_json("news.json", [])
socials_data = load_json("socials.json", {})
memes_data = load_json("memes.json", [])
pending_data = load_json("pending.json", {"news": [], "memes": [], "score_requests": [], "contact": []})
scores_data = load_json("scores.json", {})
menu_data = load_json("menu.json", {})

# ========== Тимчасові стани ==========
waiting_for: Dict[str, Any] = {}
user_class: Dict[str, str] = {}
last_click: Dict[str, float] = {}
menu_stack: Dict[str, list] = {}

# ========== Клавіатури ==========
def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📅 Розклад"), KeyboardButton(text="🔔 Розклад дзвінків")],
        [KeyboardButton(text="📰 Новини"), KeyboardButton(text="😂 Меми")],
        [KeyboardButton(text="🌐 Соцмережі школи"), KeyboardButton(text="🍽️ Меню їдальні")],
        [KeyboardButton(text="⭐ Заробити бали"), KeyboardButton(text="🛍️ Магазин")],
        [KeyboardButton(text="✏️ Змінити клас"), KeyboardButton(text="✉️ Зв’язатись з автором")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Адмін-меню")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def class_selection_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3"), KeyboardButton(text="4")],
        [KeyboardButton(text="5-А"), KeyboardButton(text="5-Б"), KeyboardButton(text="6"), KeyboardButton(text="7")],
        [KeyboardButton(text="8"), KeyboardButton(text="9"), KeyboardButton(text="10"), KeyboardButton(text="11")]
    ], resize_keyboard=True)

def day_selection_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Понеділок"), KeyboardButton(text="Вівторок")],
        [KeyboardButton(text="Середа"), KeyboardButton(text="Четвер")],
        [KeyboardButton(text="П’ятниця")]
    ], resize_keyboard=True)

def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👀 Перевірити пропозиції")],
        [KeyboardButton(text="📅 Змінити розклад"), KeyboardButton(text="🛍️ Змінити магазин")],
        [KeyboardButton(text="➕ Додати новину"), KeyboardButton(text="➖ Видалити новину")],
        [KeyboardButton(text="➕ Додати соцмережу"), KeyboardButton(text="➖ Видалити соцмережу")],
        [KeyboardButton(text="➕ Додати меню"), KeyboardButton(text="➖ Видалити меню")],
        [KeyboardButton(text="➕ Додати мем"), KeyboardButton(text="➖ Видалити мем")],
        [KeyboardButton(text="⚖️ Змінити бали")],
        [KeyboardButton(text="⬅️ Назад")]
    ], resize_keyboard=True)

def news_user_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📤 Додати новину"), KeyboardButton(text="👀 Переглянути новини")],
        [KeyboardButton(text="⬅️ Назад")]
    ], resize_keyboard=True)

def memes_user_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📤 Додати мем"), KeyboardButton(text="👀 Переглянути меми")],
        [KeyboardButton(text="⬅️ Назад")]
    ], resize_keyboard=True)

def earn_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Клікер 🖱️"), KeyboardButton(text="Камінь/Ножиці/Папір ✂️📄🪨")],
        [KeyboardButton(text="📤 Надіслати оцінку на перевірку")],
        [KeyboardButton(text="⬅️ Назад")]
    ], resize_keyboard=True)

# ========== Старт ==========
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    uid = str(message.from_user.id)
    users_data = load_json("users.json")

    username = message.from_user.username
    if uid not in users_data:
        users_data[uid] = {
            "name": message.from_user.full_name,
            "username": username if username else "",
            "points": 0
        }
    else:
        # якщо у користувача з'явився username — оновлюємо
        if username and not users_data[uid].get("username"):
            users_data[uid]["username"] = username

    save_json("users.json", users_data)

    await message.answer(
        "Привіт 👋",
        reply_markup=main_menu(message.from_user.id == AUTHOR_ID)
    )



@dp.message(lambda m: m.text == "✏️ Змінити клас")
async def change_class(message: types.Message):
    uid = uid_str_from_message(message)
    waiting_for[uid] = "choose_class"
    await message.answer("Оберіть новий клас:", reply_markup=class_selection_keyboard())

@dp.message(lambda m: waiting_for.get(str(m.from_user.id)) == "choose_class")
async def set_class(message: types.Message):
    uid = uid_str_from_message(message)
    chosen = message.text.strip()
    if chosen not in ["1","2","3","4","5-А","5-Б","6","7","8","9","10","11","Я вчитель"]:
        await message.answer("Оберіть клас з клавіатури.")
        return
    user_class[uid] = chosen
    waiting_for.pop(uid, None)
    await message.answer(f"Клас встановлено: {chosen}", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))

# ========== Новини ==========
@dp.message(lambda m: m.text == "📰 Новини")
async def news_menu(message: types.Message):
    await message.answer("Новини — обери дію:", reply_markup=news_user_keyboard())

@dp.message(lambda m: m.text == "👀 Переглянути новини")
async def view_news(message: types.Message):
    if not news_data:
        await message.answer("Поки що новин немає.", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
        return
    text = "\n\n".join(f"{i+1}. {n}" for i,n in enumerate(news_data))
    await message.answer("📰 Останні новини:\n\n" + text, reply_markup=main_menu(message.from_user.id == AUTHOR_ID))

# ========== Меми ==========
@dp.message(lambda m: m.text == "😂 Меми")
async def memes_menu(message: types.Message):
    await message.answer("Меми — обери:", reply_markup=memes_user_keyboard())

@dp.message(lambda m: m.text == "👀 Переглянути меми")
async def view_memes(message: types.Message):
    if not memes_data:
        await message.answer("Поки що мемів немає.", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
        return
    for item in memes_data:
        if isinstance(item, dict) and item.get("type") == "photo":
            await message.answer_photo(item["file_id"], caption=item.get("text",""))
        elif isinstance(item, dict) and item.get("type") == "video":
            await message.answer_video(item["file_id"], caption=item.get("text",""))
        elif isinstance(item, dict) and item.get("type") == "voice":
            # якщо хочеш підпис до голосу — зберігай text і відправляй його окремим повідомленням
            if item.get("text"):
                await message.answer(item.get("text"))
            await message.answer_voice(item["file_id"])
        elif isinstance(item, dict) and item.get("type") == "video_note":
            if item.get("text"):
                await message.answer(item.get("text"))
            await message.answer_video_note(item["file_id"])
        else:
            await message.answer(str(item))

    await message.answer('Це всі меми, якщо маєш якийсь, надсилай в "📤 Додати мем"\nВсі видалені меми зберігаються тут: https://t.me/arhive_mems', reply_markup=main_menu(message.from_user.id == AUTHOR_ID))

# ========== Розклад ==========
@dp.message(lambda m: m.text == "📅 Розклад")
async def ask_day_for_schedule(message: types.Message):
    uid = uid_str_from_message(message)
    if uid not in user_class:
        await message.answer("Спочатку оберіть свій клас:", reply_markup=class_selection_keyboard())
        return
    await message.answer("Оберіть день:", reply_markup=day_selection_keyboard())

@dp.message(lambda m: m.text in ["Понеділок","Вівторок","Середа","Четвер","П’ятниця"])
async def send_schedule(message: types.Message):
    uid = uid_str_from_message(message)
    if uid not in user_class:
        await message.answer("Спочатку оберіть свій клас:", reply_markup=class_selection_keyboard())
        return
    cl = user_class[uid]
    lessons = schedule_data.get(cl, {}).get(message.text, "❌ Розклад ще не додано")
    await message.answer(f"📅 Розклад для {cl} — {message.text}:\n\n{lessons}", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))

@dp.message(lambda m: m.text == "🔔 Розклад дзвінків")
async def bell_schedule(message: types.Message):
    text = ("🔔 Розклад дзвінків:\n"
        "1 урок: 08:30 – 09:15\n"
        "2 урок: 09:25 – 10:10\n"
        "3 урок: 10:20 – 11:05\n"
        "4 урок: 11:25 – 12:10\n"
        "5 урок: 12:30 – 13:15\n"
        "6 урок: 13:25 – 14:10\n"
        "7 урок: 14:20 – 15:05\n"
        "8 урок: 15:15 - 16:00")
    await message.answer(text, reply_markup=main_menu(message.from_user.id == AUTHOR_ID))

# ========== Новини ==========
@dp.message(lambda m: m.text == "📰 Новини")
async def news_menu(message: types.Message):
    await message.answer("Новини — обери дію:", reply_markup=news_user_keyboard())

@dp.message(lambda m: m.text == "👀 Переглянути новини")
async def view_news(message: types.Message):
    if not news_data:
        await message.answer("Поки що новин немає.", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
        return
    text = "\n\n".join(f"{i+1}. {n}" for i,n in enumerate(news_data))
    await message.answer("📰 Останні новини:\n\n" + text, reply_markup=main_menu(message.from_user.id == AUTHOR_ID))

@dp.message(lambda m: m.text == "📤 Додати новину")
async def user_add_news_prompt(message: types.Message):
    uid = uid_str_from_message(message)
    waiting_for[uid] = "user_add_news"
    await message.answer("Введи текст новини (вона піде адміну на перевірку):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

# Адмін — додати новину відразу
@dp.message(lambda m: m.text == "➕ Додати новину" and m.from_user.id == AUTHOR_ID)
async def admin_add_news_prompt(message: types.Message):
    uid = uid_str_from_message(message)
    waiting_for[uid] = "admin_add_news"
    await message.answer("Введи текст новини (воно одразу додасться):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

# Видалити новину (адмін)
@dp.message(lambda m: m.text == "➖ Видалити новину" and m.from_user.id == AUTHOR_ID)
async def admin_delete_news_prompt(message: types.Message):
    if not news_data:
        await message.answer("Поки що новин немає.", reply_markup=admin_menu_keyboard())
        return
    text = "Список новин:\n" + "\n".join(f"{i+1}. {n}" for i,n in enumerate(news_data))
    waiting_for[str(message.from_user.id)] = "admin_delete_news"
    await message.answer(text + "\n\nВведи номер новини для видалення:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

# ========== Магазин ==========
shop_data = load_json("shop.json", {"file_id": None, "caption": ""})

@dp.message(lambda m: m.text == "🛍️ Магазин")
async def open_shop(message: types.Message):
    if shop_data.get("file_id"):
        # показуємо фото з підписом
        await message.answer_photo(shop_data["file_id"], caption=shop_data.get("caption", ""))
    else:
        await message.answer("Магазин ще не налаштований.")

# =======магазин адмін=========
@dp.message(lambda m: m.text == "🛍️ Змінити магазин" and m.from_user.id == AUTHOR_ID)
async def admin_change_shop(message: types.Message):
    waiting_for[str(message.from_user.id)] = "set_shop_photo"
    await message.answer("Надішліть нове фото магазину з підписом.")

@dp.message(lambda m: waiting_for.get(str(m.from_user.id)) == "set_shop_photo" and (m.photo or m.document))
async def save_shop_photo(message: types.Message):
    uid = str(message.from_user.id)
    waiting_for.pop(uid, None)

    if message.photo:
        file_id = message.photo[-1].file_id
    else:
        file_id = message.document.file_id

    shop_data["file_id"] = file_id
    shop_data["caption"] = message.caption or ""
    save_json("shop.json", shop_data)

    await message.answer("✅ Фото магазину оновлено.", reply_markup=admin_menu_keyboard())

# ========== Меми ==========
@dp.message(lambda m: m.text == "😂 Меми")
async def memes_menu(message: types.Message):
    await message.answer("Меми — обери:", reply_markup=memes_user_keyboard())

@dp.message(lambda m: m.text == "👀 Переглянути меми")
async def view_memes(message: types.Message):
    if not memes_data:
        await message.answer("Поки що мемів немає.", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
        return
    for item in memes_data:
        if isinstance(item, dict) and item.get("type") == "photo":
            await message.answer_photo(item["file_id"], caption=item.get("text",""))
        elif isinstance(item, dict) and item.get("type") == "video":
            await message.answer_video(item["file_id"], caption=item.get("text",""))
        else:
            await message.answer(str(item))
    await message.answer('Це всі меми, якщо маєш якийсь, надсилай в "📤 Додати мем"\nВсі видалені меми зберігаються тут: https://t.me/arhive_mems', reply_markup=main_menu(message.from_user.id == AUTHOR_ID))

@dp.message(lambda m: m.text == "📤 Додати мем")
async def user_add_meme_prompt(message: types.Message):
    uid = uid_str_from_message(message)
    waiting_for[uid] = "user_add_meme"
    await message.answer("Надішли фото/відео мему або текст (підпишись, можна додати підпис). Воно піде адміну на перевірку.", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

# Адмін — додати мем одразу
@dp.message(lambda m: m.text == "➕ Додати мем" and m.from_user.id == AUTHOR_ID)
async def admin_add_meme_prompt(message: types.Message):
    uid = uid_str_from_message(message)
    waiting_for[uid] = "admin_add_meme"
    await message.answer("Надішли фото/відео мему або текст (воно одразу додасться):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

# Видалити мем (адмін)
@dp.message(lambda m: m.text == "➖ Видалити мем" and m.from_user.id == AUTHOR_ID)
async def admin_delete_meme_prompt(message: types.Message):
    if not memes_data:
        await message.answer("Поки що мемів немає.", reply_markup=admin_menu_keyboard())
        return
    text_lines = []
    for i, item in enumerate(memes_data):
        if isinstance(item, dict) and item.get("type") == "photo":
            text_lines.append(f"{i+1}. [ФОТО] {item.get('text','')[:30]}")
        elif isinstance(item, dict) and item.get("type") == "video":
            text_lines.append(f"{i+1}. [ВІДЕО] {item.get('text','')[:30]}")
        else:
            text_lines.append(f"{i+1}. {str(item)[:40]}")
    waiting_for[str(message.from_user.id)] = "admin_delete_meme"
    await message.answer("Список мемів:\n" + "\n".join(text_lines) + "\n\nВведи номер мему для видалення:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

# ========== Соцмережі ==========
@dp.message(lambda m: m.text == "🌐 Соцмережі школи")
async def show_socials(message: types.Message):
    if not socials_data:
        await message.answer("Поки що сторінок немає.", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
        return
    text = "Наші сторінки:\n" + "\n".join(f"{k}: {v}" for k,v in socials_data.items())
    await message.answer(text, reply_markup=main_menu(message.from_user.id == AUTHOR_ID))

@dp.message(lambda m: m.text == "➕ Додати соцмережу" and m.from_user.id == AUTHOR_ID)
async def admin_add_social_prompt(message: types.Message):
    waiting_for[str(message.from_user.id)] = "admin_add_social"
    await message.answer("Введи у форматі: Назва | Посилання", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

@dp.message(lambda m: m.text == "➖ Видалити соцмережу" and m.from_user.id == AUTHOR_ID)
async def admin_delete_social_prompt(message: types.Message):
    if not socials_data:
        await message.answer("Соцмереж поки немає.", reply_markup=admin_menu_keyboard())
        return
    text = "Список соцмереж:\n" + "\n".join(f"{i+1}. {name}: {link}" for i, (name, link) in enumerate(socials_data.items()))
    waiting_for[str(message.from_user.id)] = "admin_delete_social"
    await message.answer(text + "\n\nВведи назву або номер соцмережі для видалення:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

@dp.message(lambda m: m.text == "⚖️ Змінити бали" and m.from_user.id == AUTHOR_ID)
async def admin_change_points(message: types.Message):
    users_data = load_json("users.json")
    if not users_data:
        await message.answer("Немає користувачів у базі.")
        return

    text = "📋 Список користувачів:\n\n"
    for uid, info in users_data.items():
        uname = f"@{info['username']}" if info.get("username") else f"ID:{uid}"
        text += f"{uname}\n👤 {info.get('name','Без імені')}\n🏆 Бали: {info.get('points',0)}\n\n"

    waiting_for[str(message.from_user.id)] = "admin_change_points"
    await message.answer(
        text + "✍️ Введи у форматі:\n`ID +10` або `@username -5`",
        parse_mode="Markdown"
    )


# ========== Меню їдальні ==========
@dp.message(lambda m: m.text == "🍽️ Меню їдальні")
async def show_menu(message: types.Message):
    today = str(datetime.date.today())
    info = menu_data.get(today)
    if not info:
        await message.answer("❌ Меню на сьогодні ще не додано.", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
        return
    if info.get("photo"):
        await message.answer_photo(info["photo"], caption=info.get("text",""), reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
    else:
        await message.answer(f"🍽️ Меню на {today}:\n\n{info.get('text','')}", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))

@dp.message(lambda m: m.text == "➕ Додати меню" and m.from_user.id == AUTHOR_ID)
async def admin_add_menu_prompt(message: types.Message):
    waiting_for[str(message.from_user.id)] = "admin_add_menu"
    await message.answer("Надішли текст меню або фото (воно встановиться на сьогодні):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

@dp.message(lambda m: m.text == "➖ Видалити меню" and m.from_user.id == AUTHOR_ID)
async def admin_delete_menu_today(message: types.Message):
    today = str(datetime.date.today())
    if today in menu_data:
        del menu_data[today]
        save_json("menu.json", menu_data)
        await message.answer("Меню на сьогодні видалено.", reply_markup=admin_menu_keyboard())
    else:
        await message.answer("Меню на сьогодні відсутнє.", reply_markup=admin_menu_keyboard())

# ========== Зв'язок з автором ==========
@dp.message(lambda m: m.text == "✉️ Зв’язатись з автором")
async def contact_author(message: types.Message):
    uid = uid_str_from_message(message)
    waiting_for[uid] = "contact_author"
    await message.answer("Напиши повідомлення автору (текст/фото/відео з підписом). Воно піде адміну на перевірку.", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

# ========== Заробити бали (клікер, RPS, заявка на бали) ==========
@dp.message(lambda m: m.text == "⭐ Заробити бали")
async def earn_menu(message: types.Message):
    uid = uid_str_from_message(message)
    bal = scores_data.get(uid, 0)
    await message.answer(f"Твій баланс: {bal} ⭐\nОбери спосіб:", reply_markup=earn_menu_keyboard())

# Клікер
@dp.message(lambda m: m.text == "Клікер 🖱️")
async def clicker_start(message: types.Message):
    uid = uid_str_from_message(message)
    waiting_for[uid] = "clicker_mode"
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Натиснути!")],[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
    await message.answer("Натисни 'Натиснути!'. Оплата раз на 60s (0.3–1.0⭐).", reply_markup=kb)

@dp.message(lambda m: m.text == "Натиснути!")
async def clicker_press(message: types.Message):
    uid = uid_str_from_message(message)
    if waiting_for.get(uid) != "clicker_mode": return
    now = time.time()
    if now - last_click.get(uid,0) < 60:
        rem = int(60 - (now - last_click.get(uid,0)))
        await message.answer(f"Почекай {rem}s перед наступним кліком.")
        return
    gain = round(random.uniform(0.3,1.0),2)
    scores_data[uid] = round(scores_data.get(uid,0) + gain,2)
    save_json("scores.json", scores_data)
    last_click[uid] = now
    await message.answer(f"Отримано +{gain}⭐. Баланс: {scores_data[uid]}⭐")

# RPS
@dp.message(lambda m: m.text and m.text.startswith("Камінь/Ножиці/Папір"))
async def rps_prompt(message: types.Message):
    uid = uid_str_from_message(message)
    waiting_for[uid] = "rps_waiting_bet"
    await message.answer("Вкажи ставку в балах (число):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

@dp.message(lambda m: waiting_for.get(str(m.from_user.id)) == "rps_waiting_bet")
async def rps_receive_bet(message: types.Message):
    uid = uid_str_from_message(message)
    try:
        bet = float(message.text.strip())
    except Exception:
        await message.answer("Введи число (наприклад: 1).")
        return
    if bet <= 0 or bet > scores_data.get(uid,0):
        await message.answer("Некоректна ставка або недостатньо балів.")
        return
    waiting_for[uid] = {"action":"rps_choose","bet":bet}
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Камінь"),KeyboardButton(text="Ножиці"),KeyboardButton(text="Папір")],[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
    await message.answer("Оберіть: Камінь / Ножиці / Папір", reply_markup=kb)

@dp.message(lambda m: isinstance(waiting_for.get(str(m.from_user.id)), dict) and waiting_for.get(str(m.from_user.id)).get("action") == "rps_choose")
async def rps_choose(message: types.Message):
    uid = uid_str_from_message(message)
    mapping = {"камінь":"rock","ножиці":"scissors","папір":"paper",
               "rock":"rock","scissors":"scissors","paper":"paper"}
    choice = message.text.strip().lower()
    if choice not in mapping:
        await message.answer("Вибери 'Камінь', 'Ножиці' або 'Папір'.")
        return
    user_choice = mapping[choice]
    bot_choice = random.choice(["rock","scissors","paper"])
    bet = float(waiting_for[uid]["bet"])
    wins = {("rock","scissors"), ("scissors","paper"), ("paper","rock")}
    if user_choice == bot_choice:
        result_text = "Нічия. Ставка повертається."
    elif (user_choice, bot_choice) in wins:
        scores_data[uid] = round(scores_data.get(uid,0) + bet,2)
        result_text = f"Ти виграв! +{bet}⭐"
    else:
        scores_data[uid] = round(scores_data.get(uid,0) - bet,2)
        result_text = f"Ти програв. -{bet}⭐"
    save_json("scores.json", scores_data)
    waiting_for.pop(uid, None)
    await message.answer(f"Твій вибір: {user_choice}\nБот: {bot_choice}\n{result_text}\nБаланс: {scores_data.get(uid,0)}⭐", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))

# Надіслати оцінку на перевірку (можна фото+текст)
@dp.message(lambda m: m.text == "📤 Надіслати оцінку на перевірку")
async def send_score_request_prompt(message: types.Message):
    uid = uid_str_from_message(message)
    waiting_for[uid] = "submit_grade"
    await message.answer("Надішли заявку з описом та (опційно) фото/відео (підпиши).", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))

# ========== Адмін панель ==========
@dp.message(lambda m: m.text == "⚙️ Адмін-меню" and m.from_user.id == AUTHOR_ID)
async def admin_panel(message: types.Message):
    await message.answer("⚙️ Адмін-панель:", reply_markup=admin_menu_keyboard())

@dp.message(lambda m: m.text == "👀 Перевірити пропозиції" and m.from_user.id == AUTHOR_ID)
async def admin_check_pending(message: types.Message):
    counts = {
        "news": len(pending_data.get("news", [])),
        "memes": len(pending_data.get("memes", [])),
        "scores": len(pending_data.get("score_requests", [])),
        "contact": len(pending_data.get("contact", []))
    }
    text = (f"Очікують на перевірку:\n"
            f"Новини: {counts['news']}\nМеми: {counts['memes']}\nЗаявки на бали: {counts['scores']}\nПовідомлення автору: {counts['contact']}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Переглянути новини", callback_data="admin_pending_news")],
        [InlineKeyboardButton(text="Переглянути меми", callback_data="admin_pending_memes")],
        [InlineKeyboardButton(text="Переглянути заявки на бали", callback_data="admin_pending_scores")],
        [InlineKeyboardButton(text="Переглянути повідомлення автору", callback_data="admin_pending_contact")]
    ])
    await message.answer(text, reply_markup=kb)

# Інші адмін кнопки: додати/видалити мем/новину/розклад обробляються нижче у generic_handler або окремих хендлерах

# ========== Відправка наступного елементу адміну (функції) ==========
async def send_next_pending_news_to_admin(chat_id: int):
    items = pending_data.get("news", [])
    if not items:
        await bot.send_message(chat_id, "Нема новин на перевірку.", reply_markup=admin_menu_keyboard())
        return
    item = items[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Підтвердити", callback_data="approve_news"),
         InlineKeyboardButton(text="❌ Відхилити", callback_data="reject_news")]
    ])
    header = f"📣 Нова заявка на новину від {item.get('from_username') or item.get('from_id')} ({item.get('time')}):\n\n"
    if item.get("type") == "photo":
        await bot.send_photo(chat_id, item["file_id"], caption=header + (item.get("text","")), reply_markup=kb)
    elif item.get("type") == "video":
        await bot.send_video(chat_id, item["file_id"], caption=header + (item.get("text","")), reply_markup=kb)
    elif item.get("type") == "voice":
        await bot.send_message(chat_id, header + (item.get("text","")))
        await bot.send_voice(chat_id, item["file_id"], reply_markup=kb)
    elif item.get("type") == "video_note":
        await bot.send_message(chat_id, header + (item.get("text","")))
        await bot.send_video_note(chat_id, item["file_id"], reply_markup=kb)
    else:
        await bot.send_message(chat_id, header + item.get("text",""), reply_markup=kb)


async def send_next_pending_meme_to_admin(chat_id: int):
    items = pending_data.get("memes", [])
    if not items:
        await bot.send_message(chat_id, "Нема мемів на перевірку.", reply_markup=admin_menu_keyboard())
        return
    item = items[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Підтвердити", callback_data="approve_meme"),
         InlineKeyboardButton(text="❌ Відхилити", callback_data="reject_meme")]
    ])
    if item.get("type") == "photo":
        await bot.send_photo(chat_id, item["file_id"], caption=f"Мем від {display_name_from_item(item)}\n{item.get('text','')}", reply_markup=kb)
    elif item.get("type") == "video":
        await bot.send_video(chat_id, item["file_id"], caption=f"Мем від {display_name_from_item(item)}\n{item.get('text','')}", reply_markup=kb)
    elif item.get("type") == "voice":
        await bot.send_message(chat_id, f"Мем (голос) від {display_name_from_item(item)}")
        await bot.send_voice(chat_id, item["file_id"], reply_markup=kb)
    elif item.get("type") == "video_note":
        await bot.send_message(chat_id, f"Мем (відео-кружок) від {display_name_from_item(item)}")
        await bot.send_video_note(chat_id, item["file_id"], reply_markup=kb)

    else:
        await bot.send_message(chat_id, f"Мем від {display_name_from_item(item)}:\n{item.get('text')}", reply_markup=kb)

async def send_next_pending_score_to_admin(chat_id: int):
    items = pending_data.get("score_requests", [])
    if not items:
        await bot.send_message(chat_id, "Нема заявок на бали.", reply_markup=admin_menu_keyboard())
        return
    item = items[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Підтвердити і нарахувати", callback_data="approve_score"),
         InlineKeyboardButton(text="❌ Відхилити", callback_data="reject_score")]
    ])
    if item.get("type") == "photo":
        await bot.send_photo(chat_id, item["file_id"], caption=f"Заявка від {display_name_from_item(item)}\n{item.get('text','')}", reply_markup=kb)
    elif item.get("type") == "video":
        await bot.send_video(chat_id, item["file_id"], caption=f"Заявка від {display_name_from_item(item)}\n{item.get('text','')}", reply_markup=kb)
    elif item.get("type") == "voice":
        await bot.send_message(chat_id, f"Заявка від (голос) від {display_name_from_item(item)}")
        await bot.send_voice(chat_id, item["file_id"], reply_markup=kb)
    elif item.get("type") == "video_note":
        await bot.send_message(chat_id, f"Заявка від (відео-кружок) від {display_name_from_item(item)}")
        await bot.send_video_note(chat_id, item["file_id"], reply_markup=kb)
    else:
        await bot.send_message(chat_id, f"Заявка від {display_name_from_item(item)}:\n{item.get('text')}", reply_markup=kb)

async def send_next_pending_contact_to_admin(chat_id: int):
    items = pending_data.get("contact", [])
    if not items:
        await bot.send_message(chat_id, "Нема повідомлень автору.", reply_markup=admin_menu_keyboard())
        return
    item = items[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Відповісти користувачу", callback_data="reply_contact"),
         InlineKeyboardButton(text="❌ Відхилити", callback_data="reject_contact")]
    ])
    if item.get("type") == "photo":
        await bot.send_photo(chat_id, item["file_id"], caption=f"Повідомлення від {display_name_from_item(item)}\n{item.get('text','')}", reply_markup=kb)
    elif item.get("type") == "video":
        await bot.send_video(chat_id, item["file_id"], caption=f"Повідомлення від {display_name_from_item(item)}\n{item.get('text','')}", reply_markup=kb)
    elif item.get("type") == "voice":
        await bot.send_message(chat_id, f"Повідомлення від (голос) від {display_name_from_item(item)}")
        await bot.send_voice(chat_id, item["file_id"], reply_markup=kb)
    elif item.get("type") == "video_note":
        await bot.send_message(chat_id, f"Повідомлення від (відео-кружок) від {display_name_from_item(item)}")
        await bot.send_video_note(chat_id, item["file_id"], reply_markup=kb)
    else:
        await bot.send_message(chat_id, f"Повідомлення від {display_name_from_item(item)}:\n{item.get('text')}", reply_markup=kb)

# ========== CALLBACKS для перегляду черг ==========
@dp.callback_query(lambda c: c.data == "admin_pending_news" and c.from_user.id == AUTHOR_ID)
async def cb_admin_pending_news(cb: types.CallbackQuery):
    await send_next_pending_news_to_admin(cb.from_user.id)
    await cb.answer()

@dp.callback_query(lambda c: c.data == "admin_pending_memes" and c.from_user.id == AUTHOR_ID)
async def cb_admin_pending_memes(cb: types.CallbackQuery):
    await send_next_pending_meme_to_admin(cb.from_user.id)
    await cb.answer()

@dp.callback_query(lambda c: c.data == "admin_pending_scores" and c.from_user.id == AUTHOR_ID)
async def cb_admin_pending_scores(cb: types.CallbackQuery):
    await send_next_pending_score_to_admin(cb.from_user.id)
    await cb.answer()

@dp.callback_query(lambda c: c.data == "admin_pending_contact" and c.from_user.id == AUTHOR_ID)
async def cb_admin_pending_contact(cb: types.CallbackQuery):
    await send_next_pending_contact_to_admin(cb.from_user.id)
    await cb.answer()

# ========== CALLBACKS: Дії по черзі (approve/reject) ==========
# Новини
@dp.callback_query(lambda c: c.data == "approve_news" and c.from_user.id == AUTHOR_ID)
async def cb_approve_news(cb: types.CallbackQuery):
    items = pending_data.get("news", [])
    if not items:
        await cb.answer("Нема новин.", show_alert=True)
        return
    item = items.pop(0)
    news_data.append(item["text"])
    save_json("news.json", news_data)
    save_json("pending.json", pending_data)
    # повідомити автора
    try:
        await bot.send_message(item["from_id"], "Ваша новина підтверджена та додана. Дякуємо!")
    except Exception:
        pass
    # показати наступний або повернути в адмін-меню
    if pending_data.get("news"):
        await send_next_pending_news_to_admin(cb.from_user.id)
    else:
        await bot.send_message(cb.from_user.id, "Всі новини оброблено.", reply_markup=admin_menu_keyboard())
    await cb.answer("Новина підтверджена.")

@dp.callback_query(lambda c: c.data == "reject_news" and c.from_user.id == AUTHOR_ID)
async def cb_reject_news(cb: types.CallbackQuery):
    items = pending_data.get("news", [])
    if not items:
        await cb.answer("Нема новин.", show_alert=True)
        return
    item = items.pop(0)
    save_json("pending.json", pending_data)
    try:
        await bot.send_message(item["from_id"], "Ваша новина відхилена адміністратором.")
    except Exception:
        pass
    if pending_data.get("news"):
        await send_next_pending_news_to_admin(cb.from_user.id)
    else:
        await bot.send_message(cb.from_user.id, "Всі новини оброблено.", reply_markup=admin_menu_keyboard())
    await cb.answer("Новина відхилена.")

# Меми
@dp.callback_query(lambda c: c.data == "approve_meme" and c.from_user.id == AUTHOR_ID)
async def cb_approve_meme(cb: types.CallbackQuery):
    items = pending_data.get("memes", [])
    if not items:
        await cb.answer("Нема мемів.", show_alert=True)
        return

    # беремо перший мем із черги
    item = items.pop(0)

    # додаємо у memes_data залежно від типу
    if item.get("type") == "photo":
        memes_data.append({
            "type": "photo",
            "file_id": item["file_id"],
            "text": item.get("text", "")
        })
    elif item.get("type") == "video":
        memes_data.append({
            "type": "video",
            "file_id": item["file_id"],
            "text": item.get("text", "")
        })
    else:
        memes_data.append(item.get("text", ""))

    # зберігаємо у файли
    save_json("memes.json", memes_data)
    save_json("pending.json", pending_data)

    # повідомляємо користувача
    try:
        await bot.send_message(item["from_id"], "✅ Ваш мем підтверджено і додано!")
    except Exception:
        pass

    # показуємо наступний мем або повертаємося в адмін-меню
    if pending_data.get("memes"):
        await send_next_pending_meme_to_admin(cb.from_user.id)
    else:
        await bot.send_message(cb.from_user.id, "Всі меми оброблено.", reply_markup=admin_menu_keyboard())

    await cb.answer("Мем підтверджено.")


@dp.callback_query(lambda c: c.data == "reject_meme" and c.from_user.id == AUTHOR_ID)
async def cb_reject_meme(cb: types.CallbackQuery):
    items = pending_data.get("memes", [])
    if not items:
        await cb.answer("Нема мемів.", show_alert=True)
        return
    item = items.pop(0)
    save_json("pending.json", pending_data)
    try:
        await bot.send_message(item["from_id"], "Ваш мем було відхилено адміністратором.")
    except Exception:
        pass
    if pending_data.get("memes"):
        await send_next_pending_meme_to_admin(cb.from_user.id)
    else:
        await bot.send_message(cb.from_user.id, "Всі меми оброблено.", reply_markup=admin_menu_keyboard())
    await cb.answer("Мем відхилено.")

# Заявки на бали
@dp.callback_query(lambda c: c.data == "approve_score" and c.from_user.id == AUTHOR_ID)
async def cb_approve_score(cb: types.CallbackQuery):
    items = pending_data.get("score_requests", [])
    if not items:
        await cb.answer("Нема заявок.", show_alert=True)
        return
    # беремо перший, але не нараховуємо одразу — просимо адміна ввести суму
    item = items.pop(0)
    save_json("pending.json", pending_data)
    admin_uid = str(cb.from_user.id)
    waiting_for[admin_uid] = {"action":"admin_confirm_score", "target_id": item["from_id"], "target_display": item.get("from_username") or str(item.get("from_id"))}
    await bot.send_message(cb.from_user.id, f"Введи, будь ласка, скільки балів нарахувати користувачу {waiting_for[admin_uid]['target_display']} (число).", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True))
    await cb.answer()

@dp.callback_query(lambda c: c.data == "reject_score" and c.from_user.id == AUTHOR_ID)
async def cb_reject_score(cb: types.CallbackQuery):
    items = pending_data.get("score_requests", [])
    if not items:
        await cb.answer("Нема заявок.", show_alert=True)
        return
    item = items.pop(0)
    save_json("pending.json", pending_data)
    try:
        await bot.send_message(item["from_id"], "Ваша заявка на бали була відхилена адміністратором.")
    except Exception:
        pass
    if pending_data.get("score_requests"):
        await send_next_pending_score_to_admin(cb.from_user.id)
    else:
        await bot.send_message(cb.from_user.id, "Всі заявки на бали оброблено.", reply_markup=admin_menu_keyboard())
    await cb.answer("Заявка відхилена.")

# Повідомлення автору (contact)
@dp.callback_query(lambda c: c.data == "reply_contact" and c.from_user.id == AUTHOR_ID)
async def cb_reply_contact(cb: types.CallbackQuery):
    items = pending_data.get("contact", [])
    if not items:
        await cb.answer("Нема повідомлень.", show_alert=True)
        return
    item = items[0]  # не видаляємо ще — дочекаємось відповіді
    # встановлюємо стан для адміна: він має відправити текст/фото/відео, який ми потім надішлемо користувачу
    waiting_for[str(cb.from_user.id)] = {"action":"admin_reply_contact", "target_id": item["from_id"]}
    await bot.send_message(cb.from_user.id, f"Введи відповідь користувачу {display_name_from_item(item)} (можна текст або надіслати фото/відео з підписом).")
    await cb.answer()

@dp.callback_query(lambda c: c.data == "reject_contact" and c.from_user.id == AUTHOR_ID)
async def cb_reject_contact(cb: types.CallbackQuery):
    items = pending_data.get("contact", [])
    if not items:
        await cb.answer("Нема повідомлень.", show_alert=True)
        return
    item = items.pop(0)
    save_json("pending.json", pending_data)
    try:
        await bot.send_message(item["from_id"], "Ваше повідомлення адміністратор відхилив.")
    except Exception:
        pass
    if pending_data.get("contact"):
        await send_next_pending_contact_to_admin(cb.from_user.id)
    else:
        await bot.send_message(cb.from_user.id, "Всі повідомлення оброблено.", reply_markup=admin_menu_keyboard())
    await cb.answer("Повідомлення відхилено.")

# ========== Обробка загальних повідомлень коли waiting_for встановлений ==========
@dp.message()
async def generic_handler(message: types.Message):
    uid = uid_str_from_message(message)
    text = message.text or ""
    state = waiting_for.get(uid)

    if state == "admin_change_points" and message.from_user.id == AUTHOR_ID:
        try:
            key, diff = text.split()
            diff = int(diff)

            users_data = load_json("users.json")

            # шукаємо по ID або по username
            target_uid = None
            if key.isdigit() and key in users_data:
                target_uid = key
            else:
                for uid, info in users_data.items():
                    if info.get("username") and ("@" + info["username"]) == key:
                        target_uid = uid
                        break

            if not target_uid:
                await message.answer("❌ Користувач не знайдений.")
                return

            users_data[target_uid]["points"] = users_data[target_uid].get("points", 0) + diff
            save_json("users.json", users_data)

            waiting_for.pop(str(message.from_user.id), None)
            await message.answer(
                f"✅ Оновлено! У {users_data[target_uid].get('name')} тепер {users_data[target_uid]['points']} балів.",
                reply_markup=admin_menu_keyboard()
            )
        except Exception:
            await message.answer("❌ Неправильний формат. Використовуй: `ID +10` або `@username -5`")
        return


    # Кнопка "⬅️ Назад"
    if text == "⬅️ Назад":
        waiting_for.pop(uid, None)
        stack = menu_stack.get(uid, [])
        if stack:
            prev_menu = stack.pop()  # беремо попереднє меню
            await message.answer("Повертаюсь назад.", reply_markup=prev_menu)
        else:
            await message.answer("Повертаюсь у головне меню.", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
        menu_stack[uid] = stack
        return


        # ADMIN: видалити соцмережу
    if state == "admin_delete_social" and message.from_user.id == AUTHOR_ID:
        try:
            key = text.strip()
            if key.isdigit():
                idx = int(key) - 1
                name = list(socials_data.keys())[idx]
            else:
                name = key
            removed = socials_data.pop(name)
            save_json("socials.json", socials_data)
            waiting_for.pop(uid, None)
            await message.answer(f"Видалено соцмережу: {name} ({removed})", reply_markup=admin_menu_keyboard())
        except Exception:
            await message.answer("Некоректне введення.")
        return

    # USER: додати новину (йде у pending)
    if state == "user_add_news":
        item = {"from_id": int(message.from_user.id), "from_username": message.from_user.username, "time": now_str()}
        if message.photo:
            item.update({"type":"photo", "file_id": message.photo[-1].file_id, "text": message.caption or ""})
        elif message.video:
            item.update({"type":"video", "file_id": message.video.file_id, "text": message.caption or ""})
        elif message.voice:
            item.update({"type":"voice", "file_id": message.voice.file_id, "text": ""})
        elif message.video_note:
            item.update({"type":"video_note", "file_id": message.video_note.file_id, "text": ""})
        else:
            item.update({"type":"text", "text": text})
        pending_data.setdefault("news", []).append(item)
        save_json("pending.json", pending_data)
        waiting_for.pop(uid, None)
        await message.answer("Дякую! Твоя новина відправлена адміну на перевірку.", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
        return


    # ADMIN: додати новину одразу
    if state == "admin_add_news" and message.from_user.id == AUTHOR_ID:
        news_data.append(text)
        save_json("news.json", news_data)
        waiting_for.pop(uid, None)
        await message.answer("Новина додана.", reply_markup=admin_menu_keyboard())
        return

    # USER: додати мем (можна фото/відео/текст)
    if state == "user_add_meme":
        item = {"from_id": int(message.from_user.id), "from_username": message.from_user.username, "time": now_str()}
        if message.photo:
            item.update({"type":"photo", "file_id": message.photo[-1].file_id, "text": message.caption or ""})
        elif message.video:
            item.update({"type":"video", "file_id": message.video.file_id, "text": message.caption or ""})
        elif message.voice:
            item.update({"type":"voice", "file_id": message.voice.file_id, "text": ""})
        elif message.video_note:
            item.update({"type":"video_note", "file_id": message.video_note.file_id, "text": ""})
        else:
            item.update({"type":"text", "text": text})
        pending_data.setdefault("memes", []).append(item)
        save_json("pending.json", pending_data)
        waiting_for.pop(uid, None)
        await message.answer("Мем відправлено адміну на перевірку.", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
        return


    # ADMIN: додати мем одразу
    if state == "admin_add_meme" and message.from_user.id == AUTHOR_ID:
        if message.photo:
            memes_data.append({"type":"photo", "file_id": message.photo[-1].file_id, "text": message.caption or ""})
        elif message.video:
            memes_data.append({"type":"video", "file_id": message.video.file_id, "text": message.caption or ""})
        elif message.voice:
            memes_data.append({"type":"voice", "file_id": message.voice.file_id, "text": ""})
        elif message.video_note:
            memes_data.append({"type":"video_note", "file_id": message.video_note.file_id, "text": ""})
        else:
            memes_data.append(text)
        save_json("memes.json", memes_data)
        waiting_for.pop(uid, None)
        await message.answer("Мем додано.", reply_markup=admin_menu_keyboard())
        return


    # ADMIN: додати меню (текст або фото)
    if state == "admin_add_menu" and message.from_user.id == AUTHOR_ID:
        today = str(datetime.date.today())
        if message.photo:
            menu_data[today] = {"text": message.caption or "", "photo": message.photo[-1].file_id}
        else:
            menu_data[today] = {"text": text, "photo": None}
        save_json("menu.json", menu_data)
        waiting_for.pop(uid, None)
        await message.answer("Меню встановлено на сьогодні.", reply_markup=admin_menu_keyboard())
        return

    # ADMIN: додати соцмережу
    if state == "admin_add_social" and message.from_user.id == AUTHOR_ID:
        try:
            name, link = [x.strip() for x in text.split("|",1)]
            socials_data[name] = link
            save_json("socials.json", socials_data)
            waiting_for.pop(uid, None)
            await message.answer(f"Соцмережа '{name}' додана.", reply_markup=admin_menu_keyboard())
        except Exception:
            await message.answer("Неправильний формат. Введи: Назва | Посилання")
        return

    # ADMIN: видалити новину (по номеру)
    if state == "admin_delete_news" and message.from_user.id == AUTHOR_ID:
        try:
            idx = int(text.strip()) - 1
            removed = news_data.pop(idx)
            save_json("news.json", news_data)
            waiting_for.pop(uid, None)
            await message.answer(f"Видалено новину: {removed}", reply_markup=admin_menu_keyboard())
        except Exception:
            await message.answer("Неправильний номер.")
        return

    # ADMIN: видалити мем (по номеру)
    if state == "admin_delete_meme" and message.from_user.id == AUTHOR_ID:
        try:
            idx = int(text.strip()) - 1
            removed = memes_data.pop(idx)
            save_json("memes.json", memes_data)
            waiting_for.pop(uid, None)
            await message.answer(f"Видалено мем #{idx+1}.", reply_markup=admin_menu_keyboard())
        except Exception:
            await message.answer("Неправильний номер.")
        return

    # USER: заявка на оцінку (можна фото+текст)
    if state == "submit_grade":
        item = {"from_id": int(message.from_user.id), "from_username": message.from_user.username, "time": now_str()}
        if message.photo:
            item.update({"type":"photo", "file_id": message.photo[-1].file_id, "text": message.caption or ""})
        elif message.video:
            item.update({"type":"video", "file_id": message.video.file_id, "text": message.caption or ""})
        elif message.voice:
            item.update({"type":"voice", "file_id": message.voice.file_id, "text": ""})
        elif message.video_note:
            item.update({"type":"video_note", "file_id": message.video_note.file_id, "text": ""})
        else:
            item.update({"type":"text", "text": text})
        pending_data.setdefault("score_requests", []).append(item)
        save_json("pending.json", pending_data)
        waiting_for.pop(uid, None)
        await message.answer("Заявка відправлена адміну на перевірку.", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
        return


    # USER: contact author (лише формує pending)
    if state == "contact_author":
        item = {"from_id": int(message.from_user.id), "from_username": message.from_user.username, "time": now_str()}
        if message.photo:
            item.update({"type":"photo", "file_id": message.photo[-1].file_id, "text": message.caption or ""})
        elif message.video:
            item.update({"type":"video", "file_id": message.video.file_id, "text": message.caption or ""})
        elif message.voice:
            item.update({"type":"voice", "file_id": message.voice.file_id, "text": ""})
        elif message.video_note:
            item.update({"type":"video_note", "file_id": message.video_note.file_id, "text": ""})
        else:
            item.update({"type":"text", "text": text})
        pending_data.setdefault("contact", []).append(item)
        save_json("pending.json", pending_data)
        waiting_for.pop(uid, None)
        await message.answer("Повідомлення відправлено адміну на перевірку.", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))
        return

    if state == "admin_remove_score_user" and message.from_user.id == AUTHOR_ID:
        target = text.strip()
        if target.startswith("@"):
            target = target[1:]
            # шукаємо по username
            found = None
            for k,v in scores_data.items():
                # тут ти можеш додати зв'язку uid->username у себе при збереженні
                # поки що перевіримо user_class
                if user_class.get(k) and message.from_user.username == target:
                    found = k
            if not found:
                await message.answer("Не знайшов такого username у базі.")
                return
            target_id = found
        else:
            target_id = target

        waiting_for[uid] = {"action":"admin_remove_score_value", "target_id": target_id}
        await message.answer(
            f"Введи кількість балів, які потрібно зняти у {target_id}:",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
        )
        return

    # ADMIN: зняти бали — вводимо суму
    if isinstance(state, dict) and state.get("action") == "admin_remove_score_value" and message.from_user.id == AUTHOR_ID:
        try:
            val = float(text.strip())
        except Exception:
            await message.answer("Введи число (може бути дробове).")
            return

        target_id = str(state["target_id"])
        scores_data[target_id] = round(scores_data.get(target_id, 0) - val, 2)
        if scores_data[target_id] < 0:
            scores_data[target_id] = 0
        save_json("scores.json", scores_data)

        waiting_for.pop(uid, None)
        try:
            await bot.send_message(int(target_id), f"Адмін зняв у тебе {val}⭐. Новий баланс: {scores_data[target_id]}⭐")
        except Exception:
            pass

        await message.answer(f"Знято {val}⭐ у користувача {target_id}. Баланс тепер: {scores_data[target_id]}⭐", reply_markup=admin_menu_keyboard())
        return
    
    # ADMIN: після approve_score — вводить кількість балів
    
    if isinstance(state, dict) and state.get("action") == "admin_confirm_score" and message.from_user.id == AUTHOR_ID:
        try:
            val = float(text.strip())
        except Exception:
            await message.answer("Введи число (може бути дробове).")
            return
        target_id = str(state["target_id"])
        scores_data[target_id] = round(scores_data.get(target_id, 0) + val, 2)
        save_json("scores.json", scores_data)
        waiting_for.pop(uid, None)
        try:
            await bot.send_message(int(target_id), f"Адмін нарахував тобі {val}⭐. Новий баланс: {scores_data[target_id]}⭐")
        except Exception:
            pass
        # Після нарахування — якщо ще заявки залишились, покажемо наступну, інакше назад в адмін меню
        if pending_data.get("score_requests"):
            await send_next_pending_score_to_admin(message.from_user.id)
        else:
            await message.answer(f"Нараховано {val}⭐ користувачу {state.get('target_display')}.", reply_markup=admin_menu_keyboard())
        return

    # ADMIN: reply contact — адмін ввів текст/приєднав фото/відео щоб відповісти користувачу
    if isinstance(state, dict) and state.get("action") == "admin_reply_contact" and message.from_user.id == AUTHOR_ID:
        target_id = state.get("target_id")
        # відправляємо відповідь користувачу і видаляємо перший елемент з queue
        try:
            if message.photo:
                await bot.send_photo(target_id, message.photo[-1].file_id, caption=message.caption or "")
            elif message.video:
                await bot.send_video(target_id, message.video.file_id, caption=message.caption or "")
            elif message.voice:
                # якщо адмін додав текст у повідомленні — надішлемо текст перед голосом
                if message.text:
                    await bot.send_message(target_id, message.text)
                await bot.send_voice(target_id, message.voice.file_id)
            elif message.video_note:
                if message.text:
                    await bot.send_message(target_id, message.text)
                await bot.send_video_note(target_id, message.video_note.file_id)
            else:
                await bot.send_message(target_id, text or "")
            # видаляємо повідомлення з pending
            if pending_data.get("contact"):
                pending_data["contact"].pop(0)
                save_json("pending.json", pending_data)
        except Exception:
            await message.answer("Не вдалося надіслати повідомлення користувачу (можливо, він заблокував бота).")

        waiting_for.pop(uid, None)
        # показати наступне повідомлення або повернутися в адмін-меню
        if pending_data.get("contact"):
            await send_next_pending_contact_to_admin(message.from_user.id)
        else:
            await message.answer("Відповідь надіслано. Черга порожня.", reply_markup=admin_menu_keyboard())
        return

    # Якщо нічого не співпало:
    await message.answer("Не розпізнаю це повідомлення.🤷‍♂️", reply_markup=main_menu(message.from_user.id == AUTHOR_ID))

# ========== Автосейв ==========
async def autosave_loop():
    while True:
        save_json("schedule.json", schedule_data)
        save_json("news.json", news_data)
        save_json("socials.json", socials_data)
        save_json("memes.json", memes_data)
        save_json("pending.json", pending_data)
        save_json("scores.json", scores_data)
        save_json("menu.json", menu_data)
        await asyncio.sleep(15)





async def handle(request):
    return web.Response(text="✅ Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()



# ========== Запуск ==========
# async def main():
#     print("Бот запускається...")
#     asyncio.create_task(autosave_loop())
#     await dp.start_polling(bot)

async def main():
    print("Бот запускається...")
    asyncio.create_task(autosave_loop())
    asyncio.create_task(start_web_server())  # 👈 додали
    await dp.start_polling(bot)




if __name__ == "__main__":
    asyncio.run(main())
