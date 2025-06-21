import asyncio
import logging
import os

from typing import Dict

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv

import db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(',') if x]
DB_PATH = os.getenv("DB_PATH", db.DB_PATH)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ----------------------- Data -----------------------

drugs: Dict[str, Dict[str, object]] = {
    "ragvizax": {
        "name": "Рагвизакс",
        "desc": "\U0001F33C АСИТ-препарат против аллергии на амброзию. Снижает чувствительность к пыльце.",
        "price": 11300,
        "emoji": "\U0001F33C",
    },
    "grazax": {
        "name": "Гразакс",
        "desc": "\U0001F33F АСИТ-препарат от злаковых трав. Уменьшает сезонные проявления аллергии.",
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

# ----------------------- FSM -----------------------

class OrderStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    confirming = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()
    waiting_for_report_text = State()

# ----------------------- Helpers -----------------------

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def notify_admins(text: str) -> None:
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass

# ----------------------- Keyboards -----------------------

def get_main_menu(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="\U0001F48A Препараты", callback_data="drugs")
    kb.button(text="\U0001F4C8 Моя статистика", callback_data="my_stats")
    kb.button(text="\U0001F4E6 Подписки", callback_data="subscriptions")
    kb.button(text="\U0001F6D2 Корзина", callback_data="cart")
    kb.button(text="\U0001F41E Сообщить о проблеме", callback_data="report_problem")
    if is_admin(user_id):
        kb.button(text="\U0001F465 Админ-панель", callback_data="admin_panel")
    kb.button(text="\U0001F310 Сайт", url="https://inverseofficial.ru")
    kb.adjust(2, 2)
    return kb.as_markup()

def get_drugs_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, item in drugs.items():
        if key.endswith("_year"):
            continue
        kb.button(text=f"{item['emoji']} {item['name']} — {item['price']} ⭐", callback_data=f"view_{key}")
    kb.button(text="\U0001F519 Назад в меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()

def get_subscriptions_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, item in drugs.items():
        if key.endswith("_year"):
            kb.button(text=f"{item['emoji']} {item['name']} — {item['price']} ⭐", callback_data=f"view_{key}")
    kb.button(text="\U0001F519 Назад в меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()

def get_drug_detail_keyboard(drug_id: str, count: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if count > 0:
        kb.button(text="\u2795 Добавить ещё", callback_data=f"add_{drug_id}")
        kb.button(text="\u2796 Удалить", callback_data=f"remove_{drug_id}")
    else:
        kb.button(text="\u2795 Добавить в корзину", callback_data=f"add_{drug_id}")
    kb.button(text="\U0001F6D2 Перейти в корзину", callback_data="cart")
    kb.adjust(2, 1)
    return kb.as_markup()

def get_cart_keyboard(items: Dict[str, int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for drug_id in items:
        kb.button(text=f"\u274C Удалить один {drugs[drug_id]['name']}", callback_data=f"remove_{drug_id}")
    kb.button(text="\U0001F4B3 Оформить", callback_data="checkout")
    kb.button(text="\U0001F5D1 Очистить", callback_data="clear_cart")
    kb.button(text="\U0001F519 Назад", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()

# ----------------------- Handlers -----------------------

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await db.init_db(DB_PATH)
    await db.add_user(message.from_user.id, DB_PATH)
    await message.answer(
        "\U0001F44B Добро пожаловать в аптеку ДОКТОР - ВРАЧ!",
        reply_markup=get_main_menu(message.from_user.id),
    )

@dp.callback_query(F.data == "main")
async def cb_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "\U0001F3E0 Главное меню:", reply_markup=get_main_menu(callback.from_user.id)
    )
    await callback.answer()

@dp.callback_query(F.data == "drugs")
async def cb_drugs(callback: types.CallbackQuery):
    await callback.message.edit_text("\U0001F48A Препараты:", reply_markup=get_drugs_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "subscriptions")
async def cb_subscriptions(callback: types.CallbackQuery):
    await callback.message.edit_text("\U0001F4E6 Доступные подписки:", reply_markup=get_subscriptions_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("view_"))
async def cb_view_drug(callback: types.CallbackQuery):
    drug_id = callback.data.split("_", 1)[1]
    items = await db.get_cart(callback.from_user.id, DB_PATH)
    cart = {k: q for k, q in items}
    count = cart.get(drug_id, 0)
    d = drugs[drug_id]
    text = f"{d['emoji']} {hbold(d['name'])}\n\n{d['desc']}\nСтоимость: {d['price']} ⭐\nВ корзине: {count}"
    await callback.message.edit_text(text, reply_markup=get_drug_detail_keyboard(drug_id, count))
    await callback.answer()

@dp.callback_query(F.data.startswith("add_"))
async def cb_add(callback: types.CallbackQuery):
    drug_id = callback.data.split("_", 1)[1]
    await db.add_to_cart(callback.from_user.id, drug_id, path=DB_PATH)
    await cb_view_drug(callback)

@dp.callback_query(F.data.startswith("remove_"))
async def cb_remove(callback: types.CallbackQuery):
    drug_id = callback.data.split("_", 1)[1]
    await db.remove_from_cart(callback.from_user.id, drug_id, path=DB_PATH)
    await cb_view_drug(callback)

@dp.callback_query(F.data == "cart")
async def cb_cart(callback: types.CallbackQuery):
    items = await db.get_cart(callback.from_user.id, DB_PATH)
    if not items:
        await callback.message.edit_text(
            "\U0001F6D2 Ваша корзина пуста.", reply_markup=get_main_menu(callback.from_user.id)
        )
        return
    text = "\U0001F6D2 Корзина:\n\n"
    total = 0
    cart = {}
    for key, qty in items:
        if key not in drugs:
            continue
        cart[key] = qty
        price = drugs[key]["price"] * qty
        total += price
        text += f"{drugs[key]['emoji']} {drugs[key]['name']} × {qty} = {price} ⭐\n"
    text += f"\nВсего: {hbold(total)} ⭐"
    await callback.message.edit_text(text, reply_markup=get_cart_keyboard(cart))
    await callback.answer()

@dp.callback_query(F.data == "clear_cart")
async def cb_clear_cart(callback: types.CallbackQuery):
    await db.clear_cart(callback.from_user.id, DB_PATH)
    await callback.message.edit_text(
        "\U0001F5D1 Корзина очищена.", reply_markup=get_main_menu(callback.from_user.id)
    )
    await callback.answer()

@dp.callback_query(F.data == "checkout")
async def cb_checkout(callback: types.CallbackQuery, state: FSMContext):
    items = await db.get_cart(callback.from_user.id, DB_PATH)
    if not items:
        await callback.answer("Корзина пуста")
        return
    await state.set_state(OrderStates.waiting_for_name)
    await callback.message.answer("Введите ФИО")
    await callback.answer()

@dp.message(OrderStates.waiting_for_name)
async def order_name(message: Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await state.set_state(OrderStates.waiting_for_address)
    await message.answer("Введите адрес доставки")

@dp.message(OrderStates.waiting_for_address)
async def order_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    data = await state.get_data()
    items = await db.get_cart(message.from_user.id, DB_PATH)
    total = sum(drugs[k]["price"] * q for k, q in items if k in drugs)
    lines = [f"{drugs[k]['name']} × {q}" for k, q in items if k in drugs]
    text = (
        f"Подтверждаете заказ?\n"
        f"Товары: {', '.join(lines)}\n"
        f"Сумма: {total} ⭐\n"
        f"ФИО: {data['fio']}\n"
        f"Адрес: {data['address']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="confirm")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")],
    ])
    await state.set_state(OrderStates.confirming)
    await message.answer(text, reply_markup=kb)

@dp.callback_query(lambda c: c.data in {"confirm", "cancel"})
async def cb_confirm(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.clear()
        await callback.message.edit_text("Заказ отменён")
        await callback.answer()
        return
    data = await state.get_data()
    items = await db.get_cart(callback.from_user.id, DB_PATH)
    total = sum(drugs[k]["price"] * q for k, q in items if k in drugs)
    stars = await db.get_stars(callback.from_user.id, DB_PATH)
    if stars < total:
        await callback.message.edit_text("Недостаточно звёзд для оформления заказа")
        await state.clear()
        await callback.answer()
        return
    await db.update_stars(callback.from_user.id, -total, DB_PATH)
    await db.create_order(callback.from_user.id, items, total, data['fio'], data['address'], DB_PATH)
    await state.clear()
    await callback.message.edit_text("Заказ оформлен! Благодарим за покупку.")
    await notify_admins(
        f"Пользователь {callback.from_user.id} оформил заказ на {total} ⭐"
    )
    await callback.answer()

@dp.message(Command("stars"))
async def cmd_stars(message: Message):
    stars = await db.get_stars(message.from_user.id, DB_PATH)
    await message.answer(f"У вас {stars} ⭐")

@dp.message(Command("history"))
async def cmd_history(message: Message):
    orders = await db.get_orders(message.from_user.id, DB_PATH)
    if not orders:
        await message.answer("История заказов пуста")
        return
    lines = [f"{o['created_at']}: {o['total']} ⭐ - {o['items']}" for o in orders]
    await message.answer("\n".join(lines))

@dp.message(Command("addstars"))
async def cmd_addstars(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /addstars <user_id> <amount>")
        return
    await db.update_stars(int(parts[1]), int(parts[2]), DB_PATH)
    await message.answer("Готово")

@dp.message(Command("export"))
async def cmd_export(message: Message):
    if not is_admin(message.from_user.id):
        return
    path = await db.export_orders(DB_PATH)
    await message.answer_document(types.FSInputFile(path))

# ----------------------- Admin panel -----------------------

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="\U0001F464 Пользователи", callback_data="admin_users")
    kb.button(text="\U0001F4DD Заказы", callback_data="admin_orders")
    kb.button(text="\U0001F4E3 Рассылка", callback_data="admin_broadcast")
    kb.button(text="\U0001F4CA Статистика", callback_data="admin_stats")
    kb.button(text="\U0001F519 Назад", callback_data="main")
    kb.adjust(1)
    await callback.message.edit_text("Админ-панель:", reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    ids = await db.list_users(DB_PATH)
    text = "\n".join(str(i) for i in ids) or "Нет пользователей"
    kb = InlineKeyboardBuilder()
    kb.button(text="\U0001F519 Назад", callback_data="admin_panel")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: types.CallbackQuery):
    rows = await db.export_orders(DB_PATH, dest="admin_orders.csv")
    await bot.send_document(callback.from_user.id, types.FSInputFile(rows))
    await callback.answer("Файл отправлен")

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён")
        return
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await callback.message.edit_text("Введите текст сообщения:")
    await callback.answer()

@dp.message(AdminStates.waiting_for_broadcast_text)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    ids = await db.list_users(DB_PATH)
    for uid in ids:
        try:
            await bot.send_message(uid, f"\U0001F4E3 {message.text}")
        except Exception:
            continue
    await message.answer("Рассылка завершена")

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    orders = await db.get_orders(callback.from_user.id, DB_PATH)
    total = sum(o['total'] for o in orders)
    users = len(await db.list_users(DB_PATH))
    await callback.message.edit_text(
        f"Пользователей: {users}\nВаших заказов: {len(orders)}\nСумма заказов: {total} ⭐",
        reply_markup=get_main_menu(callback.from_user.id),
    )
    await callback.answer()

# ----------------------- Run -----------------------

async def main() -> None:
    await db.init_db(DB_PATH)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
