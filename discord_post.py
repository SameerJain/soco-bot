"""Building the Discord message and sending it through the webhook."""
import requests

from feeds import clean, published
from pictures import image


def post(webhook, c):
    entry = c["entry"]
    fields = [{"name": "Source", "value": c["source"], "inline": True}]
    if c["outlets"]:
        fields.append({"name": "Also covered by", "value": ", ".join(c["outlets"]), "inline": True})
    embed = {
        "title": clean(entry.title, 256),
        "url": entry.link,
        "description": clean(entry.get("summary"), 350),
        "fields": fields,
        "color": 0xD53EA3,  # SoCo logo pink
        "footer": {"text": "SoCo Bot • society × computing"},
        "timestamp": published(entry).isoformat(),
    }
    picture = image(entry, webhook)
    if picture:
        embed["image"] = {"url": picture}
    payload = {"username": "SoCo Bot", "embeds": [embed]}
    requests.post(webhook, json=payload, timeout=20).raise_for_status()
