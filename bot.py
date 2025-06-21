import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Tuple, List

from dotenv import load_dotenv
import telebot
from telebot import types

import db


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(',') if x]
DB_PATH = os.getenv("DB_PATH", db.DB_PATH)

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
drugs: Dict[str, Dict[str, object]] = {
    "ragvizax": {
        "name": "Рагвизакс",
        "desc": "\U0001F33C АСИТ-препарат против аллергии на амброзию.",
        "price": 11300,
        "emoji": "\U0001F33C",
    },
    "grazax": {
        "name": "Гразакс",
        "desc": "\U0001F33F АСИТ-препарат от злаковых трав.",
        "price": 8300,
        "emoji": "\U0001F33F",
    },
    "ragvizax_year": {
        "name": "Подписка на Рагвизакс",
        "desc": "\U0001F4E6 Подписка на 1 год на курс АСИТ.",
        "price": 110000,
        "emoji": "\U0001F4E6",
    },
    "grazax_year": {
        "name": "Подписка на Гразакс",
        "desc": "\U0001F4E6 Подписка на 1 год на курс лечения.",
        "price": 90000,
        "emoji": "\U0001F4E6",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def notify_admins(text: str) -> None:
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text)
        except Exception:
            continue


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------
def main_menu(user_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("\U0001F48A Препараты", callback_data="drugs"))
    kb.row(types.InlineKeyboardButton("\U0001F4C8 Моя статистика", callback_data="my_stats"))
    kb.row(types.InlineKeyboardButton("\U0001F4E6 Подписки", callback_data="subscriptions"))
    kb.row(types.InlineKeyboardButton("\U0001F6D2 Корзина", callback_data="cart"))
    if is_admin(user_id):
        kb.row(types.InlineKeyboardButton("\U0001F465 Админ", callback_data="admin"))
    return kb


def drugs_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    for key, item in drugs.items():
        if key.endswith("_year"):
            continue
        kb.add(types.InlineKeyboardButton(f"{item['emoji']} {item['name']} — {item['price']} ⭐", callback_data=f"view_{key}"))
    kb.add(types.InlineKeyboardButton("\U0001F519 Назад", callback_data="main"))
    return kb


def subs_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    for key, item in drugs.items():
        if key.endswith("_year"):
            kb.add(types.InlineKeyboardButton(f"{item['emoji']} {item['name']} — {item['price']} ⭐", callback_data=f"view_{key}"))
    kb.add(types.InlineKeyboardButton("\U0001F519 Назад", callback_data="main"))
    return kb


def drug_detail_keyboard(drug_id: str, count: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    if count > 0:
        kb.add(types.InlineKeyboardButton("\u2795 Добавить", callback_data=f"add_{drug_id}"))
        kb.add(types.InlineKeyboardButton("\u2796 Удалить", callback_data=f"remove_{drug_id}"))
    else:
        kb.add(types.InlineKeyboardButton("\u2795 Добавить", callback_data=f"add_{drug_id}"))
    kb.add(types.InlineKeyboardButton("\U0001F6D2 Корзина", callback_data="cart"))
    return kb


def cart_keyboard(items: Dict[str, int]) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    for drug_id in items:
        kb.add(types.InlineKeyboardButton(f"\u274C Удалить {drugs[drug_id]['name']}", callback_data=f"remove_{drug_id}"))
    if items:
        kb.add(types.InlineKeyboardButton("\U0001F4B3 Оформить", callback_data="checkout"))
        kb.add(types.InlineKeyboardButton("\U0001F5D1 Очистить", callback_data="clear_cart"))
    kb.add(types.InlineKeyboardButton("\U0001F519 Назад", callback_data="main"))
    return kb


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------
user_states: Dict[int, Dict[str, str]] = {}


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message) -> None:
    db.init_db(DB_PATH)
    db.add_user(message.from_user.id, DB_PATH)
    bot.send_message(message.chat.id, "\U0001F44B Добро пожаловать в аптеку ДОКТОР - ВРАЧ!", reply_markup=main_menu(message.from_user.id))


@bot.callback_query_handler(func=lambda c: c.data == "main")
def cb_main(call: types.CallbackQuery) -> None:
    bot.edit_message_text("\U0001F3E0 Главное меню:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu(call.from_user.id))
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "drugs")
def cb_drugs(call: types.CallbackQuery) -> None:
    bot.edit_message_text("\U0001F48A Препараты:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=drugs_keyboard())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "subscriptions")
def cb_subs(call: types.CallbackQuery) -> None:
    bot.edit_message_text("\U0001F4E6 Подписки:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=subs_keyboard())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("view_"))
def cb_view(call: types.CallbackQuery) -> None:
    drug_id = call.data.split("_", 1)[1]
    items = dict(db.get_cart(call.from_user.id, DB_PATH))
    count = items.get(drug_id, 0)
    d = drugs[drug_id]
    text = f"{d['emoji']} <b>{d['name']}</b>\n\n{d['desc']}\nСтоимость: {d['price']} ⭐\nВ корзине: {count}"
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=drug_detail_keyboard(drug_id, count))
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("add_"))
def cb_add(call: types.CallbackQuery) -> None:
    drug_id = call.data.split("_", 1)[1]
    db.add_to_cart(call.from_user.id, drug_id, path=DB_PATH)
    notify_admins(f"Пользователь {call.from_user.id} добавил {drugs[drug_id]['name']}")
    cb_view(call)


@bot.callback_query_handler(func=lambda c: c.data.startswith("remove_"))
def cb_remove(call: types.CallbackQuery) -> None:
    drug_id = call.data.split("_", 1)[1]
    db.remove_from_cart(call.from_user.id, drug_id, path=DB_PATH)
    cb_view(call)


@bot.callback_query_handler(func=lambda c: c.data == "cart")
def cb_cart(call: types.CallbackQuery) -> None:
    items = dict(db.get_cart(call.from_user.id, DB_PATH))
    if not items:
        bot.edit_message_text("\U0001F6D2 Корзина пуста", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu(call.from_user.id))
        return
    text = "\U0001F6D2 Корзина:\n\n"
    total = 0
    for key, qty in items.items():
        total += drugs[key]["price"] * qty
        text += f"{drugs[key]['emoji']} {drugs[key]['name']} × {qty} = {drugs[key]['price'] * qty} ⭐\n"
    text += f"\nВсего: <b>{total}</b> ⭐"
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=cart_keyboard(items))
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "clear_cart")
def cb_clear_cart(call: types.CallbackQuery) -> None:
    db.clear_cart(call.from_user.id, DB_PATH)
    bot.edit_message_text("\U0001F5D1 Корзина очищена", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu(call.from_user.id))
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "checkout")
def cb_checkout(call: types.CallbackQuery) -> None:
    items = db.get_cart(call.from_user.id, DB_PATH)
    if not items:
        bot.answer_callback_query(call.id, "Корзина пуста", show_alert=True)
        return
    user_states[call.from_user.id] = {"step": "fio"}
    bot.send_message(call.from_user.id, "Введите ФИО")
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "fio")
def order_fio(message: types.Message) -> None:
    state = user_states.get(message.from_user.id, {})
    state["fio"] = message.text
    state["step"] = "address"
    user_states[message.from_user.id] = state
    bot.send_message(message.chat.id, "Введите адрес доставки")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "address")
def order_address(message: types.Message) -> None:
    state = user_states.get(message.from_user.id, {})
    state["address"] = message.text
    items = db.get_cart(message.from_user.id, DB_PATH)
    total = sum(drugs[k]["price"] * q for k, q in items)
    lines = [f"{drugs[k]['name']} × {q}" for k, q in items]
    text = (
        f"Подтверждаете заказ?\n"
        f"Товары: {', '.join(lines)}\n"
        f"Сумма: {total} ⭐\n"
        f"ФИО: {state['fio']}\n"
        f"Адрес: {state['address']}"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Да", callback_data="confirm"))
    kb.add(types.InlineKeyboardButton("Отмена", callback_data="cancel"))
    state["step"] = "confirm"
    user_states[message.from_user.id] = state
    bot.send_message(message.chat.id, text, reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data in {"confirm", "cancel"})
def cb_confirm(call: types.CallbackQuery) -> None:
    state = user_states.get(call.from_user.id)
    if not state:
        bot.answer_callback_query(call.id)
        return
    if call.data == "cancel":
        user_states.pop(call.from_user.id, None)
        bot.edit_message_text("Заказ отменён", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.answer_callback_query(call.id)
        return
    items = db.get_cart(call.from_user.id, DB_PATH)
    total = sum(drugs[k]["price"] * q for k, q in items)
    stars = db.get_stars(call.from_user.id, DB_PATH)
    if stars < total:
        bot.edit_message_text("Недостаточно звёзд", chat_id=call.message.chat.id, message_id=call.message.message_id)
        user_states.pop(call.from_user.id, None)
        bot.answer_callback_query(call.id)
        return
    db.update_stars(call.from_user.id, -total, DB_PATH)
    db.create_order(call.from_user.id, items, total, state["fio"], state["address"], DB_PATH)
    user_states.pop(call.from_user.id, None)
    bot.edit_message_text("Заказ оформлен!", chat_id=call.message.chat.id, message_id=call.message.message_id)
    notify_admins(f"Пользователь {call.from_user.id} оформил заказ на {total} ⭐")
    bot.answer_callback_query(call.id)


@bot.message_handler(commands=["stars"])
def cmd_stars(message: types.Message) -> None:
    stars = db.get_stars(message.from_user.id, DB_PATH)
    bot.send_message(message.chat.id, f"У вас {stars} ⭐")


@bot.message_handler(commands=["history"])
def cmd_history(message: types.Message) -> None:
    orders = db.get_orders(message.from_user.id, DB_PATH)
    if not orders:
        bot.send_message(message.chat.id, "История заказов пуста")
        return
    lines = [f"{o['created_at']}: {o['total']} ⭐ - {o['items']}" for o in orders]
    bot.send_message(message.chat.id, "\n".join(lines))


@bot.message_handler(commands=["addstars"])
def cmd_addstars(message: types.Message) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.send_message(message.chat.id, "Использование: /addstars <user_id> <amount>")
        return
    db.update_stars(int(parts[1]), int(parts[2]), DB_PATH)
    bot.send_message(message.chat.id, "Готово")


@bot.message_handler(commands=["export"])
def cmd_export(message: types.Message) -> None:
    if not is_admin(message.from_user.id):
        return
    path = db.export_orders(DB_PATH)
    with open(path, "rb") as f:
        bot.send_document(message.chat.id, f)


@bot.callback_query_handler(func=lambda c: c.data == "admin")
def cb_admin(call: types.CallbackQuery) -> None:
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Доступ запрещён", show_alert=True)
        return
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Пользователи", callback_data="admin_users"))
    kb.add(types.InlineKeyboardButton("Заказы", callback_data="admin_orders"))
    kb.add(types.InlineKeyboardButton("Назад", callback_data="main"))
    bot.edit_message_text("Админ-панель:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin_users")
def cb_admin_users(call: types.CallbackQuery) -> None:
    ids = db.list_users(DB_PATH)
    text = "\n".join(str(i) for i in ids) or "Нет пользователей"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Назад", callback_data="admin"))
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin_orders")
def cb_admin_orders(call: types.CallbackQuery) -> None:
    path = db.export_orders(DB_PATH, dest="admin_orders.csv")
    with open(path, "rb") as f:
        bot.send_document(call.from_user.id, f)
    bot.answer_callback_query(call.id, "Файл отправлен")


def main() -> None:
    db.init_db(DB_PATH)
    bot.infinity_polling()


if __name__ == "__main__":
    main()

