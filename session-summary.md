# Claude Code Teaching Example: Oil Price Dashboard

## Session Summary

**Goal:** Build a live oil price dashboard from an empty directory in ~15 minutes of conversation.

**What we built:**
- A Python server (`server.py`) + single-page HTML dashboard (`index.html`)
- Real-time Brent & WTI prices via Yahoo Finance futures (5-min intervals)
- 2-day intraday price chart with Chart.js
- 5% intraday move detection with browser notifications
- Severity-scored Iran/supply disruption alert feed (6 RSS sources, keyword scoring, fuzzy dedup)

**Iteration arc (5 turns):**
1. "Build a dashboard" → full working v1 with FRED data, 90-day charts, news panel
2. "5% warning should be intraday" → added Yahoo Finance real-time prices, changed alert logic
3. "Intraday chart, drop spread/returns" → swapped 90-day EOD chart for 2-day 5-min chart
4. "Alerts not news stories" → replaced news panel with severity-scored conflict feed (6 feeds, keyword weighting, critical/high/medium classification)
5. "Remove duplicates" + "Sort by date, critical+high only" → fuzzy Jaccard dedup, date sort, severity filter

---

## Slide 1: "From Empty Directory to Live Dashboard"

**Layout:** Before/after screenshot. Left: empty terminal. Right: the dashboard.

**Key points:**
- Started with `ls -la` → empty directory
- 5 conversational turns → production-ready dashboard
- No frameworks installed, no boilerplate — just Python stdlib + one CDN script tag
- Each turn refined scope: data source, chart type, alert logic, feed quality

---

## Slide 2: "The Iteration Loop"

| Turn | User Request | What Changed |
|------|-------------|--------------|
| 1 | "Build a live dashboard" | Full working v1: FRED API, 90-day charts, news, 5% alerts |
| 2 | "5% warning should be intraday" | Added Yahoo Finance real-time, changed alert from EOD→intraday |
| 3 | "Intraday chart, drop spread/returns" | Replaced 3 charts with one 2-day 5-min chart |
| 4 | "High-frequency alerts, not news" | 6 RSS feeds, 40+ keyword severity scoring, color-coded |
| 5 | "Remove dupes, sort by recency" | Fuzzy Jaccard dedup, date sort, critical+high filter |

**Takeaway:** Short, precise instructions. Each turn builds on the last. The user steers; Claude executes.

---

## Slide 3: Stylized Conversation (single slide)

```
  ME:   Build a live dashboard tracking Brent and WTI oil prices
        with charts, Iran conflict alerts, and notifications for
        5% daily moves.

CLAUDE: [creates server.py + index.html, starts server]
        Dashboard is live at localhost:8080.
        Brent $101.04, WTI $93.39. 90-day charts, 15 Iran
        headlines, WTI triggered a -5.17% alert.

  ME:   The 5% warning should be based on intraday moves.

CLAUDE: FRED is end-of-day only. Adding Yahoo Finance futures
        for real-time prices — compares current vs prev close.
        [updates server + frontend]
        Brent $106.54 (+3.52% today), WTI $96.75 (+1.35%).
        No alert — neither hit 5%.

  ME:   Intraday chart over 2 days. Drop the spread and
        returns charts.

CLAUDE: [rewrites chart to 2-day 5-min intervals, removes two panels]
        390 data points per commodity. Done.

  ME:   Make the news panel focused on high-frequency alerts.

CLAUDE: [adds 6 RSS feeds, 40+ severity keywords, scoring engine,
        fuzzy dedup, color-coded critical/high/medium badges]
        20 alerts ranked by severity. Top: "Strait of Hormuz
        blockade" — score 40, tagged critical.

  ME:   Sort most recent first. Only critical and high.

CLAUDE: Done.
```

**Footer:** 5 turns. 2 files. 0 dependencies installed. ~250 lines of code.

---

## Technical Details

**Architecture:** Single Python server (stdlib `http.server`) serving a static HTML page with a JSON API endpoint (`/api/data`). No pip installs, no node_modules, no build step.

**Data sources:**
- Yahoo Finance chart API — real-time futures prices (BZ=F, CL=F), 2-day 5-min intervals
- FRED API — historical daily Brent (DCOILBRENTEU) and WTI (DCOILWTICO) spot prices
- Google News RSS — 6 targeted feeds covering Hormuz, Iran military, sanctions, OPEC, pipeline disruptions, Iran-Israel naval

**Alert engine:**
- 40+ keywords weighted by severity (blockade=10, airstrike=8, sanctions=5, iran=3, etc.)
- Headlines scored by cumulative keyword weight, classified critical (15+), high (8+), medium (5+)
- Fuzzy dedup via Jaccard word similarity (55% threshold) to merge rewrites of the same story
- Sorted most-recent first, filtered to critical + high only

**Frontend:** Single HTML file, Chart.js via CDN, dark theme, auto-refresh every 5 minutes, browser Notification API for 5% alerts.
