import re
import random
import string
from typing import Any


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{text[:80]}-{suffix}"


def estimate_reading_time(content: dict[str, Any]) -> int:
    """Count words in Editor.js text blocks; 200 wpm average."""
    words = 0
    blocks = content.get("blocks", [])
    for block in blocks:
        data = block.get("data", {})
        text = ""
        if "text" in data:
            text = re.sub(r"<[^>]+>", "", str(data["text"]))
        elif "items" in data:
            items = data["items"]
            if items and isinstance(items[0], dict):
                text = " ".join(str(i.get("content", "")) for i in items)
            else:
                text = " ".join(str(i) for i in items)
        words += len(text.split())
    return max(1, round(words / 200))


def paginate(page: int, limit: int) -> tuple[int, int]:
    page = max(1, page)
    limit = min(max(1, limit), 50)
    offset = (page - 1) * limit
    return limit, offset
