"""SoCo Bot: posts one high-quality society x computing story to Discord every 2 days.

Run by GitHub Actions once a day. It only posts if 2 days have passed since the last post.
  python soco_bot.py            # post if due
  python soco_bot.py --force    # post now
  python soco_bot.py --dry-run  # print the top picks, don't post or save

The code is split up by job:
  settings.py      outlets, keywords, and how often to post (start here to customize)
  feeds.py         reading RSS feeds
  ranking.py       scoring stories and picking the best one
  pictures.py      finding a picture for the post
  discord_post.py  building and sending the Discord message
"""
import json
import os
import sys
from datetime import datetime, timezone

from discord_post import post
from feeds import clean
from pictures import image, logo
from ranking import pick
from settings import POST_EVERY, STATE_FILE


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
        webhook = os.environ.get("DISCORD_WEBHOOK_URL", "")
        print(f"Top story's picture: {image(candidates[0]['entry'], webhook)}\nFallback logo: {logo(webhook)}")
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
