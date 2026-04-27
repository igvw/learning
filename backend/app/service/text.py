import json
import re
from typing import Any


def slugify_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.strip().lower()).strip("_")
    return slug or "module"


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def title_from_slug(slug: str) -> str:
    words = [word for word in slug.replace("_", " ").strip().split() if word]
    return " ".join(word[:1].upper() + word[1:] for word in words)


def json_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)
