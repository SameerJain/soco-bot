"""Choosing the story: filter to on-topic news, score it, then boost what people are paying attention to."""
import math
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import requests

from feeds import clean, fetch, norm_url, published, url_key
from settings import BUZZ_CHECK, MAX_AGE_DAYS, SKIP, SOCIETY, SOURCES, TECH, UA

STOPWORDS = set("that this with from what have will about after into over more their they them just says said "
                "could would when your than then were been here there which while where these those does".split())


def score(entry, source, now, recent_sources):
    """Source weight x topic relevance x freshness x variety. None means the story isn't eligible."""
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


def keywords(title):
    return {w for w in re.findall(r"[a-z0-9]+", clean(title).lower().replace("'s", "")) if len(w) > 3 and w not in STOPWORDS}


def same_story(title_a, title_b):
    """Headlines sharing 3+ keywords are treated as the same story from different outlets."""
    return len(keywords(title_a) & keywords(title_b)) >= 3


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


def other_outlets(candidate, recent):
    """Other outlets that ran a story with a similar headline: big stories get covered everywhere."""
    return sorted({name for name, entry in recent
                   if name != candidate["source"] and same_story(candidate["entry"].title, entry.get("title"))})


def pick(state, now):
    """All eligible stories, best first. Each is a dict with score, source, entry, points, comments, outlets."""
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
