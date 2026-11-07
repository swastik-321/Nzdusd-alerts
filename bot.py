import os, json, re, urllib.request, urllib.parse
import xml.etree.ElementTree as ET

TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"]

FEEDS = [
    "https://www.forexlive.com/feed/news",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
]
SEEN_FILE = "seen.json"

PROMPT = """You are a news filter for an NZD/USD forex trader.
Read the headline below. If it can move NZD/USD (US or NZ economic data, Fed or RBNZ actions, tariffs, sanctions, wars or escalation, China data, commodity shocks, major political events, banking stress, risk-on or risk-off shifts), reply in this exact format:

ALERT: HIGH or MEDIUM or LOW
Headline: one line
What happened: max 2 sentences
Impact on NZD/USD: Bullish, Bearish or Uncertain, with a one-line reason
What to watch next: one line

If it cannot realistically move NZD/USD, reply with exactly one word: IGNORE.
Never invent facts.

Headline: """

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"})
    return urllib.request.urlopen(req, timeout=30).read()

def items(url):
    root = ET.fromstring(fetch(url))
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        desc = re.sub("<[^>]+>", "", it.findtext("description") or "")[:300]
        if link:
            out.append((link, title, desc))
    return out

def gemini(text):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-flash-latest:generateContent?key=" + GEMINI_KEY)
    body = json.dumps({"contents": [{"parts": [{"text": PROMPT + text}]}]}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    data = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

def telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": msg}).encode()
    urllib.request.urlopen(urllib.request.Request(url, body), timeout=30)

def main():
    seen = set(json.load(open(SEEN_FILE))) if os.path.exists(SEEN_FILE) else set()
    first_run = not os.path.exists(SEEN_FILE)
    new_seen = set(seen)
    for feed in FEEDS:
        try:
            for link, title, desc in items(feed):
                if link in seen:
                    continue
                new_seen.add(link)
                if first_run:
                    continue
                try:
                    reply = gemini(title + " - " + desc)
                except Exception as e:
                    print("gemini error", e)
                    continue
                if reply.upper().startswith("IGNORE"):
                    continue
                telegram(reply + "\n\n" + link)
        except Exception as e:
            print("feed error", feed, e)
    json.dump(sorted(new_seen)[-2000:], open(SEEN_FILE, "w"))

main()
