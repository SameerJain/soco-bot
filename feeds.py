"""Reading RSS feeds and tidying up what comes out of them."""
import html
import re
from datetime import datetime, timezone

import feedparser
import requests

from settings import UA


def fetch(url):
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    resp.raise_for_status()
    return feedparser.parse(resp.content).entries


def clean(text, limit=None):
    """Strip HTML tags and extra whitespace, and shorten to `limit` characters at a word boundary."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text


def published(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime(*t[:6], tzinfo=timezone.utc) if t else None


def norm_url(url):
    return url.split("?")[0].split("#")[0].rstrip("/").lower()


def url_key(url):
    """norm_url without http(s):// and www., so the same article matches however it's linked."""
    return re.sub(r"^https?://(www\.)?", "", norm_url(url or ""))
