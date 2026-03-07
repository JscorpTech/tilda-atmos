import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Atmos credentials
ATMOS_CONSUMER_KEY    = os.environ.get("ATMOS_CONSUMER_KEY",    "lu6ZA2sKhytuCuvkzSVG2kOurP0a")
ATMOS_CONSUMER_SECRET = os.environ.get("ATMOS_CONSUMER_SECRET", "iBKm7aXVsDG9lHvW0tHI3mTMDWsa")
ATMOS_STORE_ID        = int(os.environ.get("ATMOS_STORE_ID",    "100265"))
ATMOS_API_URL         = os.environ.get("ATMOS_API_URL",         "https://apigw.atmos.uz")

# True bo'lsa har doim 1000 UZS (100000 tiyin) lik transaction yaratadi
DEBUG_MODE = os.environ.get("DEBUG_MODE", "true").lower() == "true"

# Muvaffaqiyatli to'lovdan keyin foydalanuvchi shu sahifaga yo'naltiriladi
FINAL_REDIRECT_URL = os.environ.get("FINAL_REDIRECT_URL", "https://ventureforum.asia/")

DB_FILE  = os.environ.get("DB_FILE",  os.path.join(BASE_DIR, "database.sqlite"))
LOG_FILE = os.environ.get("LOG_FILE", os.path.join(BASE_DIR, "post_log.txt"))
