# SoCo Bot

A Discord news bot for the club that posts **one high-quality story every 2 days** about the intersection of **society and computing** and of **news and technology**: privacy, AI and work, platforms and democracy, tech policy, journalism and tech, the digital divide, and similar topics.

Free to run: it uses GitHub Actions (no server) and a Discord webhook (no bot hosting). No API keys and no AI: once the webhook is set up, it runs on its own.

## How it picks a story

1. Pulls RSS feeds from curated outlets: The Markup, Rest of World, Tech Policy Press, MIT Technology Review, Nieman Lab, EFF, 404 Media, The Conversation, Ars Technica, Wired, The Verge, The Guardian, NPR, CACM, and CJR.
2. Drops roundups, podcasts, deals, reviews, and anything older than 7 days.
3. General outlets only count if a story hits **both** a tech keyword and a society keyword. Focused outlets (The Markup, EFF, and others) always count.
4. Scores each story by source quality × relevance × freshness, and penalizes the sources used in the last 2 posts so the picks stay varied.
5. Boosts the top 25 by how much attention they're getting. News sites don't publish traffic numbers, so the bot uses two public stand-ins: the story's points and comments on Hacker News, and how many other outlets in the list are running the same story.
6. Posts the highest-scoring story, then records it in `posted.json` so it's never posted twice. That file lives on the `bot-state` branch, so the bot never commits to `main` and your pushes don't conflict with it.

The workflow runs daily, but the bot only posts if 2 days have passed since the last post. So it posts every 2 days no matter how busy or quiet the news cycle is.

## Setup (5 minutes)

1. **Create a webhook in Discord.** Go to the channel's *Edit Channel → Integrations → Webhooks → New Webhook*, name it `SoCo Bot`, optionally add an avatar, and click *Copy Webhook URL*.
2. **Add the secret on GitHub.** In the repo, go to *Settings → Secrets and variables → Actions → New repository secret*. Set the name to `DISCORD_WEBHOOK_URL` and paste the URL as the value.
3. **Test it.** Go to *Actions → SoCo Bot → Run workflow*:
   - `dry-run` prints the top 10 candidates with their Hacker News and outlet counts, without posting.
   - `force` posts one right now.
   - `due` does what the daily schedule does.

## Customizing

Everything you'd normally change lives in `settings.py`:

- `SOURCES` holds the feeds: `(name, url, weight, focused)`. A higher weight means the source is preferred. `focused=True` means the outlet doesn't need to match keywords.
- `TECH`, `SOCIETY`, and `SKIP` are the keyword regexes.
- `POST_EVERY` sets how often the bot posts.
- `BUZZ_CHECK` sets how many top stories get the popularity check.

The rest of the code is split up by job:

| File | What it does |
|---|---|
| `soco_bot.py` | Starts the bot: checks if a post is due, picks a story, posts it, and saves the history |
| `settings.py` | Outlets, keywords, and timing |
| `feeds.py` | Reads the RSS feeds and cleans up the text |
| `ranking.py` | Scores stories and picks the best one (topic, freshness, Hacker News, other outlets) |
| `pictures.py` | Finds a picture for the post, falling back to the SoCo logo |
| `discord_post.py` | Builds the Discord message and sends it |

To change the time of day, edit the `cron` line in `.github/workflows/soco.yml` (it's in UTC).

## Run locally

```bash
pip install -r requirements.txt
python soco_bot.py --dry-run
DISCORD_WEBHOOK_URL=... python soco_bot.py --force
```
