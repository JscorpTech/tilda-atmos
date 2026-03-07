import logging
from datetime import datetime

from config import LOG_FILE

# uvicorn logger — terminal ga chiqaradi
_logger = logging.getLogger("atmos")


def log(label: str, data=None, level: str = "info") -> None:
    msg = f"{label}"
    if data is not None:
        msg += f": {data}"

    # Terminal (uvicorn log stream)
    getattr(_logger, level)(msg)

    # Fayl
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def log_error(label: str, data=None) -> None:
    log(label, data, level="error")


def log_exception(label: str, exc: Exception) -> None:
    import traceback
    tb = traceback.format_exc()
    log(f"{label}: {exc}", tb, level="error")
