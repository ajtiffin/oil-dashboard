#!/usr/bin/env python3
"""Oil Price Dashboard Server — fetches FRED data + Iran conflict news, serves dashboard."""

import http.server
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import os
import html

FRED_API_KEY = os.environ.get("FRED_API_KEY", "c36cb21e65d41e0072e241470b22487b")
PORT = 8080

FRED_SERIES = {
    "brent": "DCOILBRENTEU",
    "wti": "DCOILWTICO",
}

import re

# Multiple targeted RSS feeds for high-frequency alert detection
ALERT_FEEDS = [
    "https://news.google.com/rss/search?q=%22Strait+of+Hormuz%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Iran+strike+OR+attack+OR+military+OR+bomb+oil&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Iran+sanctions+oil+crude&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=OPEC+cut+OR+output+OR+production+OR+emergency&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=oil+pipeline+attack+OR+disruption+OR+explosion+OR+sabotage&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Iran+Israel+oil+OR+tanker+OR+naval&hl=en-US&gl=US&ceid=US:en",
]

# Keywords scored by severity — higher = more critical
SEVERITY_KEYWORDS = {
    # Critical — direct supply disruption
    "strait of hormuz": 10, "hormuz": 10, "blockade": 10, "tanker seized": 10,
    "pipeline attack": 9, "pipeline explosion": 9, "refinery attack": 9,
    "oil embargo": 9, "export ban": 9, "supply shut": 9,
    # High — military escalation with oil implications
    "airstrike": 8, "air strike": 8, "missile strike": 8, "bombing": 8,
    "military strike": 8, "naval clash": 8, "tanker attack": 8,
    "war": 7, "invasion": 7, "retaliation": 7, "escalation": 7,
    "nuclear facility": 7, "enrichment": 6,
    # Medium — sanctions / policy
    "sanctions": 5, "new sanctions": 6, "sanction waiver": 5,
    "opec cut": 6, "production cut": 6, "output cut": 6, "emergency meeting": 6,
    "export decline": 5, "supply disruption": 6,
    # Lower — context
    "iran": 3, "oil price": 2, "crude": 2, "tanker": 3,
    "israel": 3, "persian gulf": 4, "middle east": 2,
}

# Yahoo Finance futures tickers for real-time prices
YAHOO_TICKERS = {
    "brent": "BZ=F",
    "wti": "CL=F",
}


def fetch_realtime_price(ticker):
    """Fetch 2-day intraday data from Yahoo Finance (5-min intervals)."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?range=2d&interval=5m"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        result = data["chart"]["result"][0]
        meta = result["meta"]
        timestamps = result.get("timestamp", [])
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])

        # Build intraday timeseries
        intraday = []
        for ts, close in zip(timestamps, closes):
            if close is not None:
                intraday.append({
                    "timestamp": ts,
                    "time": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
                    "value": round(close, 2),
                })

        price = meta.get("regularMarketPrice")
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
        return {"price": price, "prev_close": prev_close, "intraday": intraday}
    except Exception as e:
        print(f"[Yahoo] Error fetching {ticker}: {e}")
        return None


def fetch_fred_series(series_id, limit=90):
    """Fetch daily observations from FRED API."""
    params = urllib.parse.urlencode({
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    })
    url = f"https://api.stlouisfed.org/fred/series/observations?{params}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())
    # Filter out missing values and reverse to chronological order
    obs = [
        {"date": o["date"], "value": float(o["value"])}
        for o in data.get("observations", [])
        if o["value"] != "."
    ]
    obs.reverse()
    return obs


def score_headline(title):
    """Score a headline by keyword severity. Returns (score, matched keywords)."""
    lower = title.lower()
    score = 0
    matched = []
    for keyword, weight in SEVERITY_KEYWORDS.items():
        if keyword in lower:
            score += weight
            if weight >= 5:
                matched.append(keyword)
    return score, matched


def classify_severity(score):
    """Map numeric score to severity level."""
    if score >= 15:
        return "critical"
    elif score >= 8:
        return "high"
    elif score >= 5:
        return "medium"
    return "low"


def title_words(title):
    """Extract significant words from a title for fuzzy matching."""
    stop = {"a","an","the","and","or","of","in","on","to","for","is","are","at","by","as","it","its","with","from","that","this","was","has","have","be","will","not","but","about","how","what","who","why","when","where","which","their","they","than","into","been","could","would","should","after","before","over","between","through","during","amid","says","said","new","may","can","do","does","did","up"}
    words = set(re.findall(r'[a-z]{3,}', title.lower())) - stop
    return words


def is_duplicate(new_words, existing_items, threshold=0.55):
    """Check if a title is too similar to any already-accepted item."""
    if not new_words:
        return True
    for item in existing_items:
        overlap = len(new_words & item["_words"])
        union = len(new_words | item["_words"])
        if union > 0 and overlap / union >= threshold:
            return True
    return False


def fetch_conflict_alerts():
    """Fetch headlines from multiple feeds, score by severity, deduplicate, and rank."""
    seen_exact = set()
    candidates = []

    # Collect all items from all feeds
    for feed_url in ALERT_FEEDS:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                tree = ET.parse(resp)
            for item in tree.findall(".//item"):
                title = item.findtext("title", "").strip()
                norm = re.sub(r'\s+', ' ', title.lower().strip())
                if norm in seen_exact or not title:
                    continue
                seen_exact.add(norm)

                score, keywords = score_headline(title)
                if score >= 4:
                    candidates.append({
                        "title": html.escape(title),
                        "link": item.findtext("link", ""),
                        "date": item.findtext("pubDate", ""),
                        "source": html.escape(item.findtext("source", "")),
                        "score": score,
                        "severity": classify_severity(score),
                        "tags": keywords[:3],
                        "_words": title_words(title),
                    })
        except Exception as e:
            print(f"[RSS] Error fetching feed: {e}")

    # Filter to critical and high only
    candidates = [c for c in candidates if c["severity"] in ("critical", "high")]

    # Sort by score descending so we keep the highest-scored version of similar stories
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Fuzzy dedup: greedily accept items that aren't too similar to already-accepted ones
    accepted = []
    for item in candidates:
        if not is_duplicate(item["_words"], accepted):
            accepted.append(item)
        if len(accepted) >= 20:
            break

    # Sort accepted items by date, most recent first
    def parse_date(d):
        try:
            return datetime.strptime(d, "%a, %d %b %Y %H:%M:%S %Z")
        except Exception:
            try:
                return datetime.strptime(d, "%a, %d %b %Y %H:%M:%S %z").replace(tzinfo=None)
            except Exception:
                return datetime.min

    accepted.sort(key=lambda x: parse_date(x["date"]), reverse=True)

    # Strip internal fields
    for item in accepted:
        del item["_words"]

    return accepted


def compute_dubai_ratio():
    """Compute Dubai/Brent price ratio from recent FRED monthly data."""
    try:
        dubai = fetch_fred_series("POILDUBUSDM", limit=6)
        brent_m = fetch_fred_series("POILBREUSDM", limit=6)
        if not dubai or not brent_m:
            return 0.97  # fallback
        # Average ratio over available months
        dubai_map = {d["date"]: d["value"] for d in dubai}
        ratios = []
        for b in brent_m:
            if b["date"] in dubai_map and b["value"] > 0:
                ratios.append(dubai_map[b["date"]] / b["value"])
        return sum(ratios) / len(ratios) if ratios else 0.97
    except Exception as e:
        print(f"[FRED] Error computing Dubai ratio: {e}")
        return 0.97


# Cache the Dubai/Brent ratio (recompute at most once per hour)
_dubai_ratio_cache = {"ratio": None, "timestamp": 0}


def get_dubai_ratio():
    """Get cached Dubai/Brent ratio, refreshing hourly."""
    now = datetime.now().timestamp()
    if _dubai_ratio_cache["ratio"] is None or now - _dubai_ratio_cache["timestamp"] > 3600:
        _dubai_ratio_cache["ratio"] = compute_dubai_ratio()
        _dubai_ratio_cache["timestamp"] = now
        print(f"[Dubai] Ratio updated: {_dubai_ratio_cache['ratio']:.4f}")
    return _dubai_ratio_cache["ratio"]


def get_dashboard_data():
    """Assemble all dashboard data."""
    news = fetch_conflict_alerts()

    # Fetch real-time prices + 2-day intraday from Yahoo Finance
    realtime = {}
    for name, ticker in YAHOO_TICKERS.items():
        rt = fetch_realtime_price(ticker)
        if rt and rt["price"]:
            realtime[name] = rt

    # Estimate Dubai Fateh from Brent using historical ratio
    dubai_ratio = get_dubai_ratio()
    brent_rt = realtime.get("brent")
    if brent_rt and brent_rt.get("intraday"):
        dubai_intraday = [
            {"timestamp": p["timestamp"], "time": p["time"], "value": round(p["value"] * dubai_ratio, 2)}
            for p in brent_rt["intraday"]
        ]
        dubai_price = round(brent_rt["price"] * dubai_ratio, 2)
        dubai_prev = round(brent_rt["prev_close"] * dubai_ratio, 2) if brent_rt.get("prev_close") else None
        realtime["dubai"] = {
            "price": dubai_price,
            "prev_close": dubai_prev,
            "intraday": dubai_intraday,
            "estimated": True,
            "ratio": round(dubai_ratio, 4),
        }

    # Compute APSP (IMF oil price index) = simple average of Brent, WTI, Dubai
    apsp = None
    apsp_prev = None
    if all(realtime.get(k, {}).get("price") for k in ["brent", "wti", "dubai"]):
        apsp = round((realtime["brent"]["price"] + realtime["wti"]["price"] + realtime["dubai"]["price"]) / 3, 2)
        if all(realtime.get(k, {}).get("prev_close") for k in ["brent", "wti", "dubai"]):
            apsp_prev = round((realtime["brent"]["prev_close"] + realtime["wti"]["prev_close"] + realtime["dubai"]["prev_close"]) / 3, 2)
        # Build APSP intraday from component series
        brent_intra = {p["time"]: p["value"] for p in realtime["brent"]["intraday"]}
        wti_intra = {p["time"]: p["value"] for p in realtime["wti"]["intraday"]}
        dubai_intra = {p["time"]: p["value"] for p in realtime["dubai"]["intraday"]}
        all_times = sorted(set(brent_intra) & set(wti_intra) & set(dubai_intra))
        apsp_intraday = [
            {"time": t, "value": round((brent_intra[t] + wti_intra[t] + dubai_intra[t]) / 3, 2)}
            for t in all_times
        ]
        realtime["apsp"] = {
            "price": apsp,
            "prev_close": apsp_prev,
            "intraday": apsp_intraday,
        }

    # 5% intraday alert: compare current real-time price vs previous close
    alerts = []
    for key, label in [("brent", "Brent"), ("wti", "WTI"), ("dubai", "Dubai Fateh"), ("apsp", "IMF APSP")]:
        rt = realtime.get(key)
        if rt and rt.get("price") and rt.get("prev_close"):
            prev = rt["prev_close"]
            curr = rt["price"]
            pct = ((curr - prev) / prev) * 100
            if abs(pct) >= 5:
                alerts.append({
                    "commodity": label,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "prev": prev,
                    "curr": curr,
                    "pct": round(pct, 2),
                    "source": "intraday",
                })

    return {"news": news, "alerts": alerts, "realtime": realtime}


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            try:
                data = get_dashboard_data()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(("", PORT), DashboardHandler)
    print(f"Oil Dashboard running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
