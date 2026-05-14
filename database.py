import aiosqlite
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = "bot_database.db"

DEFAULT_SETTINGS = {
    "bot_info": "🔐 Добро пожаловать! Это бот для продажи лицензионных ключей.\n\nМы предоставляем надёжный доступ к нашему программному обеспечению с различными тарифными планами.",
    "mono_card": "4441 1111 2222 3333",
    "mono_name": "Іван І.",
    "privat_card": "5168 7421 0000 1234",
    "privat_name": "Іван І.",
    "plans": {
        "1":  {"name": "1 день",    "rub": 60,   "uah": 30,   "usd": 0.7,  "days": 1,  "funpay": "https://funpay.com/lots/offer?id=63922916"},
        "3":  {"name": "3 дня",     "rub": 120,  "uah": 65,   "usd": 1.5,  "days": 3,  "funpay": "https://funpay.com/lots/offer?id=63922923"},
        "7":  {"name": "7 дней",    "rub": 240,  "uah": 130,  "usd": 3.0,  "days": 7,  "funpay": "https://funpay.com/lots/offer?id=63922934"},
        "14": {"name": "14 дней",   "rub": 370,  "uah": 200,  "usd": 4.6,  "days": 14, "funpay": "https://funpay.com/lots/offer?id=63922942"},
        "30": {"name": "30 дней",   "rub": 590,  "uah": 310,  "usd": 7.1,  "days": 30, "funpay": "https://funpay.com/lots/offer?id=63922957"},
        "90": {"name": "90 дней",   "rub": 1320, "uah": 700,  "usd": 16.0, "days": 90, "funpay": "https://funpay.com/lots/offer?id=63922969"},
        "0":  {"name": "Навсегда",  "rub": 2500, "uah": 1350, "usd": 30.0, "days": 0,  "funpay": "https://funpay.com/lots/offer?id=63922981"},
    }
}


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                plan_key TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                paid_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_key TEXT NOT NULL,
                license_key TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS available_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT UNIQUE NOT NULL,
                plan_key TEXT NOT NULL,
                status TEXT DEFAULT 'available',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                issued_at TEXT,
                issued_to_user_id INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bank_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT,
                plan_key TEXT NOT NULL,
                bank TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'UAH',
                status TEXT DEFAULT 'pending',
                admin_message_id INTEGER,
                admin_chat_id INTEGER,
                receipt_file_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT
            )
        """)
        await db.commit()

        # Migration: add receipt_file_id column if missing (for existing databases)
        try:
            await db.execute("ALTER TABLE bank_requests ADD COLUMN receipt_file_id TEXT")
            await db.commit()
            logger.info("Migration: added receipt_file_id column")
        except Exception:
            pass  # Column already exists

        for key, value in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, json.dumps(value) if isinstance(value, dict) else value)
            )
        await db.commit()
    logger.info("Database initialized")


async def get_setting(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except (json.JSONDecodeError, TypeError):
                    return row[0]
    return None


async def set_setting(key: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        val = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, val)
        )
        await db.commit()


async def save_invoice(invoice_id: str, user_id: int, plan_key: str, amount: float, currency: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO invoices (invoice_id, user_id, plan_key, amount, currency) VALUES (?, ?, ?, ?, ?)",
            (invoice_id, user_id, plan_key, amount, currency)
        )
        await db.commit()


async def get_invoice(invoice_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                cols = [d[0] for d in cursor.description]
                return dict(zip(cols, row))
    return None


async def mark_invoice_paid(invoice_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE invoices SET status = 'paid', paid_at = ? WHERE invoice_id = ?",
            (datetime.now().isoformat(), invoice_id)
        )
        await db.commit()


async def save_purchase(user_id: int, plan_key: str, license_key: str, payment_method: str, amount: float, currency: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO purchases (user_id, plan_key, license_key, payment_method, amount, currency) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, plan_key, license_key, payment_method, amount, currency)
        )
        await db.commit()


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM purchases") as c:
            total_purchases = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(DISTINCT user_id) FROM purchases") as c:
            unique_buyers = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM invoices WHERE status = 'pending'") as c:
            pending_invoices = (await c.fetchone())[0]
    return {
        "total_purchases": total_purchases,
        "unique_buyers": unique_buyers,
        "pending_invoices": pending_invoices
    }


async def get_available_key(plan_key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, license_key FROM available_keys WHERE plan_key = ? AND status = 'available' LIMIT 1",
            (plan_key,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[1]
    return None


async def mark_key_issued(license_key: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE available_keys SET status = 'issued', issued_at = ?, issued_to_user_id = ? WHERE license_key = ?",
            (datetime.now().isoformat(), user_id, license_key)
        )
        await db.commit()


async def add_keys(keys: list[str], plan_key: str) -> int:
    added = 0
    async with aiosqlite.connect(DB_PATH) as db:
        for key in keys:
            try:
                await db.execute(
                    "INSERT OR IGNORE INTO available_keys (license_key, plan_key) VALUES (?, ?)",
                    (key, plan_key)
                )
                added += 1
            except Exception as e:
                logger.error(f"Failed to add key {key}: {e}")
        await db.commit()
    return added


async def get_available_keys_count(plan_key: str = None) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        if plan_key:
            async with db.execute(
                "SELECT COUNT(*) FROM available_keys WHERE plan_key = ? AND status = 'available'",
                (plan_key,)
            ) as cursor:
                return {plan_key: (await cursor.fetchone())[0]}
        else:
            async with db.execute(
                "SELECT plan_key, COUNT(*) FROM available_keys WHERE status = 'available' GROUP BY plan_key"
            ) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}


async def get_all_available_keys(limit: int = 100):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, license_key, plan_key, created_at FROM available_keys WHERE status = 'available' LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"id": r[0], "license_key": r[1], "plan_key": r[2], "created_at": r[3]} for r in rows]


async def get_issued_keys_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM available_keys WHERE status = 'issued'") as c:
            total_issued = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM available_keys WHERE status = 'available'") as c:
            total_available = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM available_keys") as c:
            total_keys = (await c.fetchone())[0]
    return {"total_keys": total_keys, "available": total_available, "issued": total_issued}


async def save_bank_request(user_id: int, user_name: str, plan_key: str, bank: str, amount: float) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO bank_requests (user_id, user_name, plan_key, bank, amount) VALUES (?, ?, ?, ?, ?)",
            (user_id, user_name, plan_key, bank, amount)
        )
        await db.commit()
        return cursor.lastrowid


async def update_bank_request_receipt(request_id: int, receipt_file_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bank_requests SET receipt_file_id = ? WHERE id = ?",
            (receipt_file_id, request_id)
        )
        await db.commit()


async def update_bank_request_message(request_id: int, admin_chat_id: int, admin_message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bank_requests SET admin_chat_id = ?, admin_message_id = ? WHERE id = ?",
            (admin_chat_id, admin_message_id, request_id)
        )
        await db.commit()


async def get_bank_request(request_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM bank_requests WHERE id = ?", (request_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                cols = [d[0] for d in cursor.description]
                return dict(zip(cols, row))
    return None


async def resolve_bank_request(request_id: int, status: str):
    """status: 'approved' или 'rejected'"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bank_requests SET status = ?, resolved_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), request_id)
        )
        await db.commit()


async def get_bank_requests(status: str = None, limit: int = 30) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        if status:
            async with db.execute(
                "SELECT * FROM bank_requests WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                cols = [d[0] for d in cursor.description]
                return [dict(zip(cols, r)) for r in rows]
        else:
            async with db.execute(
                "SELECT * FROM bank_requests ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                cols = [d[0] for d in cursor.description]
                return [dict(zip(cols, r)) for r in rows]


async def get_orders_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM bank_requests WHERE status = 'pending'") as c:
            pending = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM bank_requests WHERE status = 'approved'") as c:
            approved = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM bank_requests WHERE status = 'rejected'") as c:
            rejected = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM purchases") as c:
            total_purchases = (await c.fetchone())[0]
    return {
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "total_purchases": total_purchases,
    }


async def get_user_purchases(user_id: int) -> list:
    """Все покупки пользователя с деталями ключей"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT p.id, p.plan_key, p.license_key, p.payment_method, p.amount, p.currency, p.created_at,
                   k.status as key_status
            FROM purchases p
            LEFT JOIN available_keys k ON k.license_key = p.license_key
            WHERE p.user_id = ?
            ORDER BY p.created_at DESC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]


async def get_user_bank_requests(user_id: int) -> list:
    """Банковские заявки пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM bank_requests WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]


async def get_pending_bank_requests_with_buttons(limit: int = 20) -> list:
    """Ожидающие заявки для списка с кнопками в админке"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM bank_requests WHERE status = 'pending' ORDER BY created_at ASC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]


async def delete_key(key_id: int) -> bool:
    """Удаляет доступный ключ по id. Возвращает True если удалён."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM available_keys WHERE id = ? AND status = 'available'",
            (key_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_available_keys_count_total() -> int:
    """Общее количество доступных ключей."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM available_keys WHERE status = 'available'"
        ) as cursor:
            return (await cursor.fetchone())[0]


async def get_available_keys_page(offset: int = 0, limit: int = 10):
    """Возвращает страницу доступных ключей с пагинацией."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, license_key, plan_key FROM available_keys WHERE status = 'available' ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, offset)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"id": r[0], "license_key": r[1], "plan_key": r[2]} for r in rows]
