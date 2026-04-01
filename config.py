import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Atmos credentials
ATMOS_CONSUMER_KEY    = os.environ.get("ATMOS_CONSUMER_KEY",    "***REMOVED***")
ATMOS_CONSUMER_SECRET = os.environ.get("ATMOS_CONSUMER_SECRET", "***REMOVED***")
ATMOS_STORE_ID        = int(os.environ.get("ATMOS_STORE_ID",    "100265"))
ATMOS_API_URL         = os.environ.get("ATMOS_API_URL",         "https://apigw.atmos.uz")

# True bo'lsa har doim 1000 UZS (100000 tiyin) lik transaction yaratadi
DEBUG_MODE = os.environ.get("DEBUG_MODE", "true").lower() == "true"

# Muvaffaqiyatli to'lovdan keyin foydalanuvchi shu sahifaga yo'naltiriladi
FINAL_REDIRECT_URL = os.environ.get("FINAL_REDIRECT_URL", "https://ventureforum.asia/")

# Telegram bot — Tilda notify muvaffaqiyatsiz bo'lganda xabar yuborish uchun
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8737138088:AAETbG92NB2aapW9feoAzp21rhC5CGLBLg8")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "@madyageeks")

DB_FILE  = os.environ.get("DB_FILE",  os.path.join(BASE_DIR, "database.sqlite"))
LOG_FILE = os.environ.get("LOG_FILE", os.path.join(BASE_DIR, "post_log.txt"))
