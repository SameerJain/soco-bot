"""Everything you might want to tweak: which outlets to read, what counts as on-topic, and how often to post."""
from datetime import timedelta
from pathlib import Path

# (name, feed url, weight, focused). A higher weight means the outlet is preferred.
# Focused outlets cover society + tech by default; the rest must match both a
# tech keyword and a society keyword to be considered.
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

# Keyword patterns. A story is on-topic when it mentions both TECH and SOCIETY words.
# Headlines matching SKIP (roundups, podcasts, deals...) are never posted.
TECH = r"\b(ai|a\.i\.|artificial intelligence|algorithms?|machine learning|chatbots?|llms?|deepfakes?|data|software|apps?|internet|online|social media|platforms?|tiktok|meta|google|openai|youtube|digital|cyber\w*|hack\w*|encryption|computers?|computing|tech|technology|robots?|automation|facial recognition|smartphones?|streaming|crypto\w*|data centers?)\b"
SOCIETY = r"\b(privacy|surveillance|rights|civil liberties|law|laws|lawsuit|court|policy|regulat\w+|ban|bans|congress|government|election\w*|democracy|voters?|misinformation|disinformation|censorship|speech|moderation|workers?|labor|jobs|unions?|students?|schools?|education|teachers?|kids|children|teens?|parents|journalis\w+|newsrooms?|news|bias|discrimination|equity|inequality|accessibility|disability|health|climate|energy|police|policing|immigration|ethics|safety|public|communit\w+|society|social|culture|economy)\b"
SKIP = r"(podcast|^the download|newsletter|\bdeals?\b|\bsale\b|\breview\b|hands-on|\bbest \w+ (for|of)\b|gift guide|sponsored|webinar|this week in|\brecap\b|\bquiz\b|crossword|methodology|acknowledg|effector)"

POST_EVERY = timedelta(hours=36)  # daily runs + 36h = every other day, with 12h slack for late runs
MAX_AGE_DAYS = 7                  # ignore stories older than this
BUZZ_CHECK = 25                   # how many top stories get a Hacker News + cross-outlet popularity check

STATE_FILE = Path(__file__).with_name("posted.json")  # history of what's been posted
UA = "SoCoBot/1.0 (Discord news bot; +https://github.com/SameerJain/soco-bot)"
