# SoCo Bot

Posts one news story about society and computing to Discord every 2 days. It runs free on GitHub Actions.

## Setup
Go to *Actions → SoCo Bot → Run workflow* and pick a mode:
   - `dry-run`: show the top picks without posting
   - `force`: post now
   - `due`: post only if 2 days have passed

After that, it runs every morning by itself. Automatic runs show up as "Scheduled" in the Actions tab. Open a run to see whether it posted or said `Not due yet`.

## Changing things
- Outlets, keywords, and how often it posts: `settings.py`
- Time of day: the `cron` line in `.github/workflows/soco.yml` (UTC)

## Contributing
Just do the standard branch and PR for whatever it is you desire!
