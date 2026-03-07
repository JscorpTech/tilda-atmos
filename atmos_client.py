import hashlib
from base64 import b64encode
from typing import Optional
from urllib.parse import urlencode

import httpx

from config import ATMOS_API_URL, ATMOS_CONSUMER_KEY, ATMOS_CONSUMER_SECRET, ATMOS_PROXY, ATMOS_STORE_ID
from database import get_connection, get_cached_token, cache_token, get_cached_rate, cache_rates
from logger import log

FALLBACK_RATES = {
    "UZS": 25.5,
    "USD": 0.002,
    "EUR": 0.0018,
    "RUB": 0.18,
}


def _atmos_client() -> httpx.Client:
    return httpx.Client(proxy=ATMOS_PROXY, timeout=30)


def get_token() -> Optional[str]:
    conn = get_connection()
    cached = get_cached_token(conn)
    if cached:
        return cached

    credentials = b64encode(f"{ATMOS_CONSUMER_KEY}:{ATMOS_CONSUMER_SECRET}".encode()).decode()
    try:
        with _atmos_client() as client:
            resp = client.post(
                f"{ATMOS_API_URL}/token",
                content="grant_type=client_credentials",
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
    except Exception as e:
        log("Atmos Token", f"FAIL {e}")
        return None

    if resp.status_code != 200:
        log("Atmos Token", f"FAIL http={resp.status_code}")
        return None

    data = resp.json()
    token = data.get("access_token")
    if token:
        cache_token(conn, token, int(data.get("expires_in", 3600)))
        log("Atmos Token", "OK")
    return token


def create_invoice(
    token: str,
    amount_tiyin: int,
    account: str,
    desc: str,
    request_id: str,
    success_url: str,
) -> Optional[dict]:
    payload = {
        "request_id": request_id,
        "store_id":   ATMOS_STORE_ID,
        "account":    account,
        "amount":     amount_tiyin,
        "success_url": success_url,
    }
    log("Invoice Create", f"account={account} amount={amount_tiyin}")
    try:
        with _atmos_client() as client:
            resp = client.post(
                f"{ATMOS_API_URL}/checkout/invoice/create",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
    except Exception as e:
        log("Invoice Error", str(e))
        return None

    if resp.status_code != 200:
        log("Invoice Error", f"http={resp.status_code} body={resp.text[:200]}")
        return None

    data = resp.json()
    log("Invoice OK", f"payment_id={data.get('payment_id', '?')}")
    return data


def check_invoice(token: str, payment_id: int) -> Optional[dict]:
    try:
        with _atmos_client() as client:
            resp = client.post(
                f"{ATMOS_API_URL}/checkout/invoice/get",
                json={"payment_id": payment_id},
                headers={"Authorization": f"Bearer {token}"},
            )
        return resp.json()
    except Exception as e:
        log("Invoice Check Error", str(e))
        return None


def _php_str(value) -> str:
    """PHP float-to-string: 55000.0 → '55000', 55000.5 → '55000.5'"""
    try:
        f = float(value)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(value)


def compute_tilda_hash(fields: dict) -> str:
    """
    Tilda hash algoritmi:
    - hash va signature fieldlarini o'chirish
    - fieldlarni alfavit bo'yicha sort (field nomlari bo'yicha)
    - qiymatlarni separatorsiz birlashtirish
    - MD5
    """
    f = {k: str(v) for k, v in fields.items() if k not in ("hash", "signature")}
    return hashlib.md5("".join(f[k] for k in sorted(f)).encode()).hexdigest()


def notify_tilda(notification_url: str, order_id: str, amount, payment_id: int = 0) -> bool:
    fields = {
        "order_id": order_id,
        "amount":   _php_str(amount),
        "success":  "true",
        "order":    str(payment_id),
    }
    fields["hash"] = compute_tilda_hash(fields)

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                notification_url,
                content=urlencode(fields),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        log("Tilda Notify", f"order={order_id} resp={resp.text.strip()!r} http={resp.status_code}")
        return resp.status_code == 200 and resp.text.strip() == "OK"
    except Exception as e:
        log("Tilda Notify", f"order={order_id} ERROR {e}")
        return False


def get_exchange_rate(from_currency: str, to_currency: str) -> Optional[float]:
    conn = get_connection()
    cached = get_cached_rate(conn, from_currency, to_currency)
    if cached is not None:
        return cached

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"https://open.er-api.com/v6/latest/{from_currency}")
    except Exception:
        return None

    if resp.status_code != 200:
        log("Rate API Error", f"http={resp.status_code}")
        return None

    data = resp.json()
    rates = data.get("rates", {})
    if to_currency not in rates:
        log("Rate API Error", f"no rate for {to_currency}")
        return None

    cache_rates(conn, from_currency, rates)
    return float(rates[to_currency])


def convert_from_kzt(amount_kzt: float, to_currency: str) -> float:
    """Tilda dan kelgan KZT summani berilgan valyutaga konvertatsiya qiladi."""
    to_currency = to_currency.upper().strip()
    if to_currency == "KZT":
        return amount_kzt

    rate = get_exchange_rate("KZT", to_currency)
    if rate is None:
        log("Currency", f"fallback rate for {to_currency}")
        rate = FALLBACK_RATES.get(to_currency, 1.0)

    converted = round(amount_kzt * rate, 2)
    log("Currency", f"{amount_kzt} KZT → {converted} {to_currency} (rate={rate})")
    return converted
