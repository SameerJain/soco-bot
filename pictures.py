"""Finding a picture for the post. Every post gets one: the article's own, or the SoCo logo as a last resort."""
import html
import re
import sys

import requests

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
NOT_A_PICTURE = r"pixel|tracking|feedburner|doubleclick|emoji|gravatar|/1x1|spacer"


def image(entry, webhook):
    return feed_image(entry) or page_image(entry.link) or logo(webhook)


def feed_image(entry):
    """A picture listed in the RSS feed itself, skipping tracking pixels and emoji."""
    for key in ("media_content", "media_thumbnail"):
        media = [m for m in entry.get(key) or [] if m.get("url") and not re.search(NOT_A_PICTURE, m["url"], re.I)]
        if media:  # feeds often list several sizes; take the biggest
            return max(media, key=lambda m: int(m.get("width") or 0))["url"]
    for e in entry.get("enclosures") or []:
        if e.get("type", "").startswith("image") and e.get("href"):
            return e["href"]
    body = " ".join([c.get("value", "") for c in entry.get("content") or []] + [entry.get("summary") or ""])
    for tag in re.findall(r"<img\b[^>]*>", body, re.I):
        m = re.search(r"src=[\"'](https?://[^\"']+)", tag)
        if m and not re.search(NOT_A_PICTURE, m.group(1), re.I) and not re.search(r"(width|height)=[\"']?1[\"' ]", tag):
            return html.unescape(m.group(1))
    return None


def page_image(url):
    """The preview image the article page declares for link previews (og:image / twitter:image)."""
    try:
        page = requests.get(url, headers={"User-Agent": BROWSER_UA}, timeout=20).text
    except Exception as e:
        print(f"Couldn't load {url} for an image: {e}", file=sys.stderr)
        return None
    for tag in re.findall(r"<meta\b[^>]*>", page, re.I):
        if re.search(r"(property|name)=[\"'](og:image|og:image:url|twitter:image)[\"']", tag, re.I):
            m = re.search(r"content=[\"'](https?://[^\"']+)", tag, re.I)
            if m:
                return html.unescape(m.group(1))
    return None


def logo(webhook):
    """The webhook's avatar (the SoCo logo), used when a story has no picture of its own."""
    try:
        hook = requests.get(webhook, timeout=20).json()
        return f"https://cdn.discordapp.com/avatars/{hook['id']}/{hook['avatar']}.png?size=1024" if hook.get("avatar") else None
    except Exception as e:
        print(f"Couldn't load the webhook avatar: {e}", file=sys.stderr)
        return None
