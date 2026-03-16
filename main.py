import json
import time
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse

from atmos_client import convert_from_kzt, create_invoice, get_token, notify_tilda
from config import DEBUG_MODE, FINAL_REDIRECT_URL
from database import (
    get_connection,
    load_order,
    load_order_by_payment_id,
    save_order,
    update_order_status,
)
from logger import log, log_error, log_exception

app = FastAPI(title="Tilda Atmos Payment Gateway", docs_url=None, redoc_url=None)


@app.get("/")
def index():
    return PlainTextResponse("Waiting for payment request...")


@app.post("/")
async def pay(request: Request):
    try:
        return await _pay(request)
    except Exception as exc:
        log_exception("UNHANDLED ERROR in POST /", exc)
        return PlainTextResponse("Internal server error", status_code=500)


async def _pay(request: Request):
    """
    Tilda bu endpointga buyurtma ma'lumotlarini POST qiladi.
    Invoice yaratib, foydalanuvchini Atmos to'lov sahifasiga yo'naltiradi.
    """
    form = await request.form()

    amount_raw   = str(form.get("amount", "") or "0")
    order_id     = str(form.get("order_id", "") or "")
    notification = str(form.get("notification", "") or "")
    desc         = str(form.get("desc", "") or "")
    products     = str(form.get("products", "[]") or "[]")
    currency     = str(form.get("currency", "UZS") or "UZS").upper().strip()
    tilda_hash   = str(form.get("hash", "") or "")

    try:
        amount = float(amount_raw)
    except ValueError:
        amount = 0.0

    if amount <= 0 or not order_id or not notification:
        return PlainTextResponse("Missing required payment data", status_code=400)

    log("New Order", f"{order_id} amount={amount_raw} {currency}")

    token = get_token()
    if not token:
        return PlainTextResponse("Failed to get payment token", status_code=500)

    # Amount doimo KZT da keladi → UZS ga konvertatsiya → tiyin
    amount_uzs   = convert_from_kzt(amount, "UZS")
    amount_tiyin = int(amount_uzs * 100)

    if DEBUG_MODE:
        amount_tiyin = 100000  # 1000 UZS

    base_url    = str(request.base_url).rstrip("/")
    success_url = FINAL_REDIRECT_URL
    request_id  = "tilda_" + order_id.replace(":", "_") + "_" + str(int(time.time()))

    invoice = create_invoice(token, amount_tiyin, order_id, desc, request_id, success_url)

    if not invoice or not invoice.get("url"):
        log_error("ERROR", f"Invoice create failed for {order_id}")
        return PlainTextResponse("Failed to create payment", status_code=500)

    conn = get_connection()
    save_order(conn, {
        "order_id":         order_id,
        "notification_url": notification,
        "amount_original":  amount_raw,
        "currency":         currency,
        "amount_uzs":       amount_uzs,
        "amount_tiyin":     amount_tiyin,
        "payment_id":       invoice.get("payment_id"),
        "atmos_token":      invoice.get("token"),
        "description":      desc,
        "tilda_hash":       tilda_hash,
        "status":           "pending",
        "created_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    log("Redirect", order_id)
    return RedirectResponse(url=invoice["url"], status_code=302)


@app.post("/callback.php")
async def callback(request: Request):
    try:
        return await _callback(request)
    except Exception as exc:
        log_exception("UNHANDLED ERROR in /callback.php", exc)
        return JSONResponse({"status": 0, "message": "Internal error"})


async def _callback(request: Request):
    """
    Atmos to'lovni tasdiqlashdan OLDIN shu endpointga murojaat qiladi.
    status:1 qaytarilgandagina Atmos to'lovni yakunlaydi.
    """
    try:
        body = await request.body()
        data = json.loads(body)
    except Exception:
        return JSONResponse({"status": 0, "message": "Invalid JSON"})

    transaction_id = data.get("transaction_id")
    account        = data.get("account")
    invoice_id     = data.get("invoice")

    log("Callback", f"account={account} tx={transaction_id}")

    conn  = get_connection()
    order = None

    if account:
        order = load_order(conn, str(account))
    if not order and transaction_id:
        order = load_order_by_payment_id(conn, int(transaction_id))
    if not order and invoice_id:
        order = load_order_by_payment_id(conn, int(invoice_id))

    if not order:
        log("Callback ERROR", f"order not found account={account} tx={transaction_id}")
        return JSONResponse({"status": 0, "message": "Order not found"})

    if order["status"] == "paid":
        return JSONResponse({"status": 1, "message": "OK"})

    notified = notify_tilda(
        order["notification_url"],
        order["order_id"],
        order["amount_uzs"],
        int(order["payment_id"] or 0),
    )
    update_order_status(conn, order["order_id"], "paid", notified)
    log("Payment OK", f"{order['order_id']} tilda={'OK' if notified else 'FAIL'}")

    return JSONResponse({"status": 1, "message": "OK"})
