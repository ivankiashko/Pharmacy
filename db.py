import aiosqlite
from datetime import datetime
from typing import List, Tuple, Optional
import json

DB_PATH = "bot.db"

async def init_db(path: str = DB_PATH):
    async with aiosqlite.connect(path) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    stars INTEGER DEFAULT 0
                )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS cart (
                    user_id INTEGER,
                    drug_key TEXT,
                    quantity INTEGER,
                    PRIMARY KEY (user_id, drug_key)
                )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    items TEXT,
                    total INTEGER,
                    fio TEXT,
                    address TEXT,
                    created_at TEXT
                )"""
        )
        await db.commit()

async def get_user(user_id: int, path: str = DB_PATH) -> Optional[aiosqlite.Row]:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def add_user(user_id: int, path: str = DB_PATH):
    async with aiosqlite.connect(path) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id, stars) VALUES(?, 0)", (user_id,))
        await db.commit()

async def update_stars(user_id: int, delta: int, path: str = DB_PATH):
    async with aiosqlite.connect(path) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id, stars) VALUES(?, 0)", (user_id,))
        await db.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (delta, user_id))
        await db.commit()

async def get_stars(user_id: int, path: str = DB_PATH) -> int:
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def add_to_cart(user_id: int, drug_key: str, qty: int = 1, path: str = DB_PATH):
    async with aiosqlite.connect(path) as db:
        await db.execute("INSERT OR IGNORE INTO cart(user_id, drug_key, quantity) VALUES(?, ?, 0)", (user_id, drug_key))
        await db.execute("UPDATE cart SET quantity = quantity + ? WHERE user_id = ? AND drug_key = ?", (qty, user_id, drug_key))
        await db.commit()

async def clear_cart(user_id: int, path: str = DB_PATH):
    async with aiosqlite.connect(path) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_cart(user_id: int, path: str = DB_PATH) -> List[Tuple[str, int]]:
    async with aiosqlite.connect(path) as db:
        async with db.execute("SELECT drug_key, quantity FROM cart WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchall()

async def create_order(user_id: int, items: List[Tuple[str, int]], total: int, fio: str, address: str, path: str = DB_PATH):
    created_at = datetime.utcnow().isoformat()
    items_json = json.dumps(items, ensure_ascii=False)
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "INSERT INTO orders(user_id, items, total, fio, address, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, items_json, total, fio, address, created_at)
        )
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_orders(user_id: int, path: str = DB_PATH) -> List[aiosqlite.Row]:
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user_id,)) as cursor:
            return await cursor.fetchall()

async def export_orders(path: str = DB_PATH, dest: str = "orders.csv") -> str:
    import csv
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders") as cursor:
            rows = await cursor.fetchall()
    with open(dest, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "user_id", "items", "total", "fio", "address", "created_at"])
        for row in rows:
            writer.writerow([row["id"], row["user_id"], row["items"], row["total"], row["fio"], row["address"], row["created_at"]])
    return dest
