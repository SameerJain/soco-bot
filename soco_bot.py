"""SoCo Bot: posts one high-quality society x computing story to Discord every 2 days.

Run by GitHub Actions once a day. It only posts if 2 days have passed since the last post.
  python soco_bot.py            # post if due
  python soco_bot.py --force    # post now
  python soco_bot.py --dry-run  # print the top picks, don't post or save
"""
import html
import json
import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

# (name, feed url, weight, focused). Focused outlets cover society + tech by default;
# the rest must match both a tech keyword and a society keyword to be considered.
SOURCES = [
    ("The Markup",            "https://themarkup.org/feeds/rss.xml",                    1.5, True),
    ("Rest of World",         "https://restofworld.org/feed/latest/",                   1.4, True),
    ("Tech Policy Press",     "https://www.techpolicy.press/feed/",                     1.3, True),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/",                 1.3, False),
    ("Nieman Lab",            "https://www.niemanlab.org/feed/",                        1.2, True),
    ("EFF Deeplinks",         "https://www.eff.org/rss/updates.xml",                    1.2, True),
    ("404 Media",             "https://www.404media.co/rss/",                           1.2, False),
    ("The Conversation",      "https://theconversation.com/us/technology/articles.atom", 1.1, True),
    ("Ars Technica",          "https://feeds.arstechnica.com/arstechnica/tech-policy",  1.1, True),
    ("Wired",                 "https://www.wired.com/feed/category/ideas/latest/rss",   1.1, False),
    ("Wired",                 "https://www.wired.com/feed/category/politics/latest/rss", 1.1, False),
    ("The Verge",             "https://www.theverge.com/rss/policy/index.xml",          1.0, True),
    ("The Guardian",          "https://www.theguardian.com/technology/rss",             1.0, False),
    ("NPR",                   "https://feeds.npr.org/1019/rss.xml",                     1.0, False),
    ("Communications of the ACM", "https://cacm.acm.org/feed/",                         1.0, False),
    ("Columbia Journalism Review", "https://www.cjr.org/feed",                          0.9, False),
]

TECH = r"\b(ai|a\.i\.|artificial intelligence|algorithms?|machine learning|chatbots?|llms?|deepfakes?|data|software|apps?|internet|online|social media|platforms?|tiktok|meta|google|openai|youtube|digital|cyber\w*|hack\w*|encryption|computers?|computing|tech|technology|robots?|automation|facial recognition|smartphones?|streaming|crypto\w*|data centers?)\b"
SOCIETY = r"\b(privacy|surveillance|rights|civil liberties|law|laws|lawsuit|court|policy|regulat\w+|ban|bans|congress|government|election\w*|democracy|voters?|misinformation|disinformation|censorship|speech|moderation|workers?|labor|jobs|unions?|students?|schools?|education|teachers?|kids|children|teens?|parents|journalis\w+|newsrooms?|news|bias|discrimination|equity|inequality|accessibility|disability|health|climate|energy|police|policing|immigration|ethics|safety|public|communit\w+|society|social|culture|economy)\b"
SKIP = r"(podcast|^the download|newsletter|\bdeals?\b|\bsale\b|\breview\b|hands-on|\bbest \w+ (for|of)\b|gift guide|sponsored|webinar|this week in|\brecap\b|\bquiz\b|crossword|methodology|acknowledg|effector)"

STATE_FILE = Path(__file__).with_name("posted.json")
POST_EVERY = timedelta(hours=36)  # daily runs + 36h = every other day, with 12h slack for late runs
MAX_AGE_DAYS = 7
BUZZ_CHECK = 25  # how many top stories get a Hacker News + cross-outlet popularity check
UA = "SoCoBot/1.0 (Discord news bot; +https://github.com/SameerJain/soco-bot)"
STOPWORDS = set("that this with from what have will about after into over more their they them just says said "
                "could would when your than then were been here there which while where these those does".split())


def clean(text, limit=None):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text


def norm_url(url):
    return url.split("?")[0].split("#")[0].rstrip("/").lower()


def published(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime(*t[:6], tzinfo=timezone.utc) if t else None


def image(entry):
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key) or []:
            if m.get("url"):
                return m["url"]
    for e in entry.get("enclosures") or []:
        if e.get("type", "").startswith("image") and e.get("href"):
            return e["href"]
    return None


def fetch(url):
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    resp.raise_for_status()
    return feedparser.parse(resp.content).entries


def score(entry, source, now, recent_sources):
    name, _, weight, focused = source
    title, summary = clean(entry.get("title")), clean(entry.get("summary"))
    date = published(entry)
    if not title or not entry.get("link") or not date:
        return None
    age = (now - date).days
    if age > MAX_AGE_DAYS or re.search(SKIP, title, re.I):
        return None

    def hits(pattern):  # title hits count double
        return 2 * len(set(re.findall(pattern, title, re.I))) + len(set(re.findall(pattern, summary, re.I)))

    tech, soc = hits(TECH), hits(SOCIETY)
    if not focused and not (tech and soc):
        return None
    relevance = 1 + 0.15 * min(tech, 5) + 0.15 * min(soc, 5) + (0.5 if tech and soc else 0)
    freshness = 1.0 if age <= 2 else 0.8 if age <= 4 else 0.5
    variety = 0.6 if name in recent_sources else 1.0
    return weight * relevance * freshness * variety


def url_key(url):
    return re.sub(r"^https?://(www\.)?", "", norm_url(url or ""))


def keywords(title):
    return {w for w in re.findall(r"[a-z0-9]+", clean(title).lower().replace("'s", "")) if len(w) > 3 and w not in STOPWORDS}


def hacker_news(url):
    """(points, comments) the story got on Hacker News: a public, free proxy for reader traffic."""
    try:
        resp = requests.get("https://hn.algolia.com/api/v1/search", headers={"User-Agent": UA}, timeout=15,
                            params={"query": url, "restrictSearchableAttributes": "url", "hitsPerPage": 20})
        resp.raise_for_status()
        hits = [h for h in resp.json()["hits"] if url_key(h.get("url")) == url_key(url)]
    except Exception as e:
        print(f"Hacker News lookup failed for {url}: {e}", file=sys.stderr)
        return 0, 0
    return sum(h.get("points") or 0 for h in hits), sum(h.get("num_comments") or 0 for h in hits)


def same_story(title_a, title_b):
    """Headlines sharing 3+ keywords are treated as the same story from different outlets."""
    return len(keywords(title_a) & keywords(title_b)) >= 3


def other_outlets(candidate, recent):
    """Other outlets that ran a story with a similar headline: big stories get covered everywhere."""
    return sorted({name for name, entry in recent
                   if name != candidate["source"] and same_story(candidate["entry"].title, entry.get("title"))})


def pick(state, now):
    seen = {norm_url(p["url"]) for p in state["posted"]} | {p["title"].lower() for p in state["posted"]}
    # Don't post another outlet's version of a story we already posted.
    covered = [p["title"] for p in state["posted"]
               if now - datetime.fromisoformat(p["posted_at"]) <= timedelta(days=2 * MAX_AGE_DAYS)]
    recent_sources = [p["source"] for p in state["posted"][-2:]]
    candidates, recent = [], []
    for source in SOURCES:
        try:
            entries = fetch(source[1])
        except Exception as e:
            print(f"skip {source[0]} ({source[1]}): {e}", file=sys.stderr)
            continue
        for entry in entries:
            date = published(entry)
            if date and (now - date).days <= MAX_AGE_DAYS:
                recent.append((source[0], entry))
            if norm_url(entry.get("link", "")) in seen or clean(entry.get("title")).lower() in seen:
                continue
            if any(same_story(entry.get("title"), title) for title in covered):
                continue
            s = score(entry, source, now, recent_sources)
            if s:
                candidates.append({"score": s, "source": source[0], "entry": entry})

    # Re-rank the strongest matches by how much attention they're getting.
    top = sorted(candidates, key=lambda c: c["score"], reverse=True)[:BUZZ_CHECK]
    with ThreadPoolExecutor(max_workers=8) as pool:
        hn_results = list(pool.map(lambda c: hacker_news(c["entry"].link), top))
    for c, (points, comments) in zip(top, hn_results):
        c["points"], c["comments"] = points, comments
        c["outlets"] = other_outlets(c, recent)
        c["score"] *= 1 + min(math.log10(1 + points + comments) / 2.5, 1.2) + 0.15 * min(len(c["outlets"]), 4)
    return sorted(top, key=lambda c: c["score"], reverse=True)


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
    if image(entry):
        embed["image"] = {"url": image(entry)}
    payload = {"username": "SoCo Bot", "embeds": [embed]}
    requests.post(webhook, json=payload, timeout=20).raise_for_status()


def main():
    force, dry_run = "--force" in sys.argv, "--dry-run" in sys.argv
    now = datetime.now(timezone.utc)
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    state.setdefault("posted", [])

    last = state.get("last_posted_at")
    if last and not (force or dry_run) and now - datetime.fromisoformat(last) < POST_EVERY:
        print(f"Not due yet (last post {last}).")
        return

    candidates = pick(state, now)
    if not candidates:
        sys.exit("No candidate stories found.")
    if dry_run:
        for c in candidates[:10]:
            print(f"{c['score']:5.2f}  {c['source']:24.24s}  {clean(c['entry'].title)}\n"
                  f"       HN {c['points']} pts/{c['comments']} comments, also in: {', '.join(c['outlets']) or '-'}"
                  f"  {c['entry'].link}")
        return

    source, entry = candidates[0]["source"], candidates[0]["entry"]
    post(os.environ["DISCORD_WEBHOOK_URL"], candidates[0])
    state["last_posted_at"] = now.isoformat()
    state["posted"] = (state["posted"] + [{"url": entry.link, "title": clean(entry.title), "source": source,
                                           "posted_at": now.isoformat()}])[-500:]
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
    print(f"Posted: [{source}] {clean(entry.title)}")


if __name__ == "__main__":
    main()
