import os, json, re, urllib.request, urllib.parse, time
import xml.etree.ElementTree as ET

TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"]

FEEDS = [
    "https://www.forexlive.com/feed/news",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "http://feeds.feedburner.com/ndtvprofit-latest",
]
SEEN_FILE = "seen.json"

PROMPT = """You are a news filter for an NZD/USD forex trader and an Indian Nifty and Sensex F&O trader.
Read the headline below. If it can move NZD/USD (US or NZ economic data, Fed or RBNZ actions, tariffs, sanctions, wars or escalation, China data, commodity shocks, major political events, banking stress, risk-on or risk-off shifts), reply in this exact format:
Also treat it as relevant if it can move Nifty, Sensex or Bank Nifty (RBI, FII or DII flows, India data, oil, global cues, budget, big earnings). For those, start with MARKET: INDIA and write Impact on Nifty instead.
ALERT: HIGH or MEDIUM or LOW
Headline: one line
What happened: max 2 sentences
Impact on NZD/USD: Bullish, Bearish or Uncertain, with a one-line reason
What to watch next: one line

If it cannot realistically move NZD/USD, Nifty or Sensex, reply with exactly one word: IGNORE.
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
    data = json.loads(urllib.request.urlopen(req, timeout=180).read())
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

def telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": msg}).encode()
    urllib.request.urlopen(urllib.request.Request(url, body), timeout=30)

def ntfy(msg):
    try:
        req = urllib.request.Request(
            "https://ntfy.sh/newzupdate_aagya_swastikkk_030201",
            msg.encode("utf-8"),
            {"Title": "NZDUSD Alert", "Priority": "high"},
        )
        urllib.request.urlopen(req, timeout=30)
    except Exception as e:
        print("ntfy error", e)


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
                    time.sleep(6)
                    reply = gemini(title + " - " + desc)
                except Exception as e:
                    print("gemini error", e)
                    continue
                if reply.upper().startswith("IGNORE"):
                    continue
                telegram(reply + "\n\n" + link)
                ntfy(reply + "\n\n" + link)

        except Exception as e:
            print("feed error", feed, e)
    json.dump(sorted(new_seen)[-2000:], open(SEEN_FILE, "w"))

main()
