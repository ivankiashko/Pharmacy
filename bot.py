import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from typing import Dict, Tuple

import db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(',') if x]
DB_PATH = os.getenv("DB_PATH", db.DB_PATH)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Drug data

drugs: Dict[str, Dict[str, object]] = {
  "ragvizax": {
    "name": "Рагвизакс",
    "desc": "\U0001F33C АСИТ-препарат против аллергии на амброзию. Снижает чувствительность к пыльце, облегчает симптомы.",
    "price": 11300,
    "emoji": "\U0001F33C"
  },
  "grazax": {
    "name": "Гразакс",
    "desc": "\U0001F33F АСИТ-препарат от злаковых трав. Уменьшает сезонные проявления аллергии.",
    "price": 8300,
    "emoji": "\U0001F33F"
  },
  "ragvizax_year": {
    "name": "Подписка на Рагвизакс",
    "desc": "\U0001F4E6 Подписка на 1 год: регулярные поставки, курс АСИТ.",
    "price": 110000,
    "emoji": "\U0001F4E6"
  },
  "grazax_year": {
    "name": "Подписка на Гразакс",
    "desc": "\U0001F4E6 Подписка на 1 год: доставка, курс лечения.",
    "price": 90000,
    "emoji": "\U0001F4E6"
  }
}

class OrderStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    confirming = State()


# Utilities

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Keyboards

def shop_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{item['emoji']} {item['name']} - {item['price']} ⭐", callback_data=f"add:{key}")]
        for key, item in drugs.items()
    ])
    return builder

def cart_keyboard(total: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton(text="Очистить корзину", callback_data="clear")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await db.add_user(message.from_user.id, DB_PATH)
    await message.answer("Добро пожаловать в аптеку! Используйте /shop для просмотра товаров.")

@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    kb = shop_keyboard()
    text = "Выберите товар для добавления в корзину:"

@dp.callback_query(lambda c: c.data and c.data.startswith("add:"))
async def callback_add_to_cart(call: types.CallbackQuery):
    key = call.data.split(":", 1)[1]
    await db.add_to_cart(call.from_user.id, key, path=DB_PATH)
    await call.answer("Добавлено в корзину")

@dp.callback_query(lambda c: c.data == "clear")
async def callback_clear(call: types.CallbackQuery):
    await db.clear_cart(call.from_user.id, path=DB_PATH)
    await call.answer("Корзина очищена", show_alert=True)
    await call.message.edit_text("Корзина пуста")

@dp.message(Command("cart"))
async def cmd_cart(message: Message):
    items = await db.get_cart(message.from_user.id, DB_PATH)
    if not items:
        await message.answer("Корзина пуста")
        return
    lines = []
    total = 0
    for key, qty in items:
        item = drugs.get(key)
        if item:
            subtotal = item["price"] * qty
            total += subtotal
            lines.append(f"{item['emoji']} {item['name']} x {qty} = {subtotal} ⭐")
    text = "\n".join(lines) + f"\nВсего: {total} ⭐"
    await message.answer(text, reply_markup=cart_keyboard(total))

@dp.callback_query(lambda c: c.data == "checkout")
async def callback_checkout(call: types.CallbackQuery, state: FSMContext):
    items = await db.get_cart(call.from_user.id, DB_PATH)
    if not items:
        await call.answer("Корзина пуста")
        return
    await state.set_state(OrderStates.waiting_for_name)
    await call.message.answer("Введите ФИО")
    await call.answer()

@dp.message(OrderStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await state.set_state(OrderStates.waiting_for_address)
    await message.answer("Введите адрес доставки")

@dp.message(OrderStates.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    data = await state.get_data()
    items = await db.get_cart(message.from_user.id, DB_PATH)
    total = sum(drugs[key]["price"] * qty for key, qty in items if key in drugs)
    lines = [f"{drugs[k]['name']} x {q}" for k, q in items]
    text = f"Подтверждаете заказ?\n" \
           f"Товары: {', '.join(lines)}\n" \
           f"Сумма: {total} ⭐\n" \
           f"ФИО: {data['fio']}\n" \
           f"Адрес: {data['address']}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="confirm")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
    ])
    await state.set_state(OrderStates.confirming)
    await message.answer(text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data in {"confirm", "cancel"})
async def callback_confirm(call: types.CallbackQuery, state: FSMContext):
    if call.data == "cancel":
        await state.clear()
        await call.message.edit_text("Заказ отменён")
        await call.answer()
        return
    data = await state.get_data()
    items = await db.get_cart(call.from_user.id, DB_PATH)
    total = sum(drugs[key]["price"] * qty for key, qty in items if key in drugs)
    stars = await db.get_stars(call.from_user.id, DB_PATH)
    if stars < total:
        await call.message.edit_text("Недостаточно звёзд для оформления заказа")
        await state.clear()
        await call.answer()
        return
    await db.update_stars(call.from_user.id, -total, DB_PATH)
    await db.create_order(call.from_user.id, items, total, data['fio'], data['address'], DB_PATH)
    await state.clear()
    await call.message.edit_text("Заказ оформлен! Благодарим за покупку.")
    await call.answer()

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
    lines = []
    for o in orders:
        lines.append(f"{o['created_at']}: {o['total']} ⭐ - {o['items']}")
    await message.answer("\n".join(lines))

# Admin commands

@dp.message(Command("addstars"))
async def cmd_addstars(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /addstars <user_id> <amount>")
        return
    user_id = int(parts[1])
    amount = int(parts[2])
    await db.update_stars(user_id, amount, DB_PATH)
    await message.answer("Готово")

@dp.message(Command("export"))
async def cmd_export(message: Message):
    if not is_admin(message.from_user.id):
        return
    path = await db.export_orders(DB_PATH)
    await message.answer_document(types.FSInputFile(path))


async def on_startup() -> None:
    await db.init_db(DB_PATH)


async def main() -> None:
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
