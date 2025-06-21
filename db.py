import sqlite3
import json
from datetime import datetime
from typing import List, Tuple, Dict


DB_PATH = "bot.db"


def _connect(path: str = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(path)


def init_db(path: str = DB_PATH) -> None:
    with _connect(path) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                stars INTEGER DEFAULT 0
            )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS cart (
                user_id INTEGER,
                drug_key TEXT,
                quantity INTEGER,
                PRIMARY KEY (user_id, drug_key)
            )"""
        )
        db.execute(
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
        db.commit()


def add_user(user_id: int, path: str = DB_PATH) -> None:
    with _connect(path) as db:
        db.execute(
            "INSERT OR IGNORE INTO users(user_id, stars) VALUES(?, 0)",
            (user_id,),
        )
        db.commit()


def update_stars(user_id: int, delta: int, path: str = DB_PATH) -> None:
    with _connect(path) as db:
        db.execute(
            "INSERT OR IGNORE INTO users(user_id, stars) VALUES(?, 0)",
            (user_id,),
        )
        db.execute(
            "UPDATE users SET stars = stars + ? WHERE user_id = ?",
            (delta, user_id),
        )
        db.commit()


def get_stars(user_id: int, path: str = DB_PATH) -> int:
    with _connect(path) as db:
        cur = db.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row[0] if row else 0


def add_to_cart(user_id: int, drug_key: str, qty: int = 1, path: str = DB_PATH) -> None:
    with _connect(path) as db:
        db.execute(
            "INSERT OR IGNORE INTO cart(user_id, drug_key, quantity) VALUES(?, ?, 0)",
            (user_id, drug_key),
        )
        db.execute(
            "UPDATE cart SET quantity = quantity + ? WHERE user_id = ? AND drug_key = ?",
            (qty, user_id, drug_key),
        )
        db.commit()


def remove_from_cart(user_id: int, drug_key: str, qty: int = 1, path: str = DB_PATH) -> None:
    with _connect(path) as db:
        db.execute(
            "UPDATE cart SET quantity = quantity - ? WHERE user_id = ? AND drug_key = ?",
            (qty, user_id, drug_key),
        )
        db.execute(
            "DELETE FROM cart WHERE user_id = ? AND drug_key = ? AND quantity <= 0",
            (user_id, drug_key),
        )
        db.commit()


def clear_cart(user_id: int, path: str = DB_PATH) -> None:
    with _connect(path) as db:
        db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        db.commit()


def get_cart(user_id: int, path: str = DB_PATH) -> List[Tuple[str, int]]:
    with _connect(path) as db:
        cur = db.execute(
            "SELECT drug_key, quantity FROM cart WHERE user_id = ?",
            (user_id,),
        )
        return cur.fetchall()


def create_order(
    user_id: int,
    items: List[Tuple[str, int]],
    total: int,
    fio: str,
    address: str,
    path: str = DB_PATH,
) -> None:
    created_at = datetime.utcnow().isoformat()
    items_json = json.dumps(items, ensure_ascii=False)
    with _connect(path) as db:
        db.execute(
            "INSERT INTO orders(user_id, items, total, fio, address, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, items_json, total, fio, address, created_at),
        )
        db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        db.commit()


def get_orders(user_id: int, path: str = DB_PATH) -> List[Dict[str, object]]:
    with _connect(path) as db:
        cur = db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def export_orders(path: str = DB_PATH, dest: str = "orders.csv") -> str:
    with _connect(path) as db:
        cur = db.execute("SELECT * FROM orders")
        rows = cur.fetchall()
        columns = [c[0] for c in cur.description]
    import csv

    with open(dest, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)
    return dest


def list_users(path: str = DB_PATH) -> List[int]:
    with _connect(path) as db:
        cur = db.execute("SELECT user_id FROM users")
        return [r[0] for r in cur.fetchall()]
