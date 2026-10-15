# SoCo Bot

A Discord news bot for the club that posts **one high-quality story every 2 days** about the intersection of **society and computing** and of **news and technology**: privacy, AI and work, platforms and democracy, tech policy, journalism and tech, the digital divide, and similar topics.

Free to run: it uses GitHub Actions (no server) and a Discord webhook (no bot hosting).

## How it picks a story

1. Pulls RSS feeds from curated outlets: The Markup, Rest of World, Tech Policy Press, MIT Technology Review, Nieman Lab, EFF, 404 Media, The Conversation, Ars Technica, Wired, The Verge, The Guardian, NPR, CACM, and CJR.
2. Drops roundups, podcasts, deals, reviews, and anything older than 7 days.
3. General outlets only count if a story hits **both** a tech keyword and a society keyword. Focused outlets (The Markup, EFF, and others) always count.
4. Scores each story by source quality × relevance × freshness, and penalizes the sources used in the last 2 posts so the picks stay varied.
5. Posts the top story it hasn't posted before, then records it in `posted.json`.

The workflow runs daily, but the bot only posts if 2 days have passed since the last post. So it posts every 2 days no matter how busy or quiet the news cycle is.

## Setup (5 minutes)

1. **Create a webhook in Discord.** Go to the channel's *Edit Channel → Integrations → Webhooks → New Webhook*, name it `SoCo Bot`, optionally add an avatar, and click *Copy Webhook URL*.
2. **Add the secret on GitHub.** In the repo, go to *Settings → Secrets and variables → Actions → New repository secret*. Set the name to `DISCORD_WEBHOOK_URL` and paste the URL as the value.
3. **Test it.** Go to *Actions → SoCo Bot → Run workflow*:
   - `dry-run` prints the top 10 candidates in the log without posting.
   - `force` posts one right now.
   - `due` does what the daily schedule does.

## Customizing

Everything lives at the top of `soco_bot.py`:

- `SOURCES` holds the feeds: `(name, url, weight, focused)`. A higher weight means the source is preferred. `focused=True` means the outlet doesn't need to match keywords.
- `TECH`, `SOCIETY`, and `SKIP` are the keyword regexes.
- `POST_EVERY` sets how often the bot posts.

To change the time of day, edit the `cron` line in `.github/workflows/soco.yml` (it's in UTC).

## Run locally

```bash
pip install -r requirements.txt
python soco_bot.py --dry-run
DISCORD_WEBHOOK_URL=... python soco_bot.py --force
```
