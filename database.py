import json
import sqlite3
import time
from datetime import datetime
from typing import Optional

from config import DB_FILE


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id         TEXT PRIMARY KEY,
            notification_url TEXT,
            amount_original  TEXT,
            currency         TEXT,
            amount_uzs       REAL,
            amount_tiyin     INTEGER,
            payment_id       INTEGER,
            atmos_token      TEXT,
            description      TEXT,
            tilda_hash       TEXT DEFAULT '',
            status           TEXT DEFAULT 'pending',
            tilda_notified   INTEGER DEFAULT 0,
            created_at       TEXT,
            paid_at          TEXT
        );
        CREATE TABLE IF NOT EXISTS rate_cache (
            currency   TEXT PRIMARY KEY,
            rates      TEXT,
            updated_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS token_cache (
            id         INTEGER PRIMARY KEY CHECK (id = 1),
            token      TEXT,
            expires_at INTEGER
        );
    """)
    conn.commit()


def save_order(conn: sqlite3.Connection, data: dict) -> None:
    conn.execute("""
        INSERT OR REPLACE INTO orders
            (order_id, notification_url, amount_original, currency, amount_uzs, amount_tiyin,
             payment_id, atmos_token, description, tilda_hash, status, tilda_notified, created_at, paid_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["order_id"],
        data.get("notification_url", ""),
        data.get("amount_original", "0"),
        data.get("currency", "UZS"),
        data.get("amount_uzs", 0),
        data.get("amount_tiyin", 0),
        data.get("payment_id"),
        data.get("atmos_token"),
        data.get("description", ""),
        data.get("tilda_hash", ""),
        data.get("status", "pending"),
        1 if data.get("tilda_notified") else 0,
        data.get("created_at"),
        data.get("paid_at"),
    ))
    conn.commit()


def load_order(conn: sqlite3.Connection, order_id: str) -> Optional[dict]:
    row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    return dict(row) if row else None


def load_order_by_payment_id(conn: sqlite3.Connection, payment_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM orders WHERE payment_id = ?", (payment_id,)).fetchone()
    return dict(row) if row else None


def update_order_status(conn: sqlite3.Connection, order_id: str, status: str, notified: bool = False) -> None:
    paid_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == "paid" else None
    conn.execute(
        "UPDATE orders SET status = ?, tilda_notified = ?, paid_at = ? WHERE order_id = ?",
        (status, 1 if notified else 0, paid_at, order_id),
    )
    conn.commit()


def get_cached_token(conn: sqlite3.Connection) -> Optional[str]:
    row = conn.execute("SELECT token, expires_at FROM token_cache WHERE id = 1").fetchone()
    if row and row["expires_at"] > int(time.time()):
        return row["token"]
    return None


def cache_token(conn: sqlite3.Connection, token: str, expires_in: int) -> None:
    expires_at = int(time.time()) + expires_in - 60
    conn.execute(
        "INSERT OR REPLACE INTO token_cache (id, token, expires_at) VALUES (1, ?, ?)",
        (token, expires_at),
    )
    conn.commit()


def get_cached_rate(conn: sqlite3.Connection, from_currency: str, to_currency: str) -> Optional[float]:
    row = conn.execute(
        "SELECT rates, updated_at FROM rate_cache WHERE currency = ?",
        (from_currency.lower(),),
    ).fetchone()
    if row and row["updated_at"] > int(time.time()) - 3600:
        rates = json.loads(row["rates"])
        return float(rates[to_currency]) if to_currency in rates else None
    return None


def cache_rates(conn: sqlite3.Connection, from_currency: str, rates: dict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO rate_cache (currency, rates, updated_at) VALUES (?, ?, ?)",
        (from_currency.lower(), json.dumps(rates), int(time.time())),
    )
    conn.commit()
