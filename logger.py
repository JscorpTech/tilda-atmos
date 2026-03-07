from datetime import datetime
from config import LOG_FILE


def log(label: str, data=None) -> None:
    msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {label}"
    if data is not None:
        msg += f": {data}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
