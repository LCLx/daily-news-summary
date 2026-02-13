#!/usr/bin/env python3
"""
Test all RSS feeds defined in email_pipeline.py.
Checks reachability and reports article counts.
"""

import sys
import os
import socket
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import feedparser
from datetime import datetime, timedelta, timezone
from email_pipeline import RSS_SOURCES

HOURS = 24
cutoff_time = datetime.now(timezone.utc) - timedelta(hours=HOURS)


def test_feed(url):
    """
    Fetch a single feed and return a result dict.
    """
    try:
        socket.setdefaulttimeout(15)
        feed = feedparser.parse(url, agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        socket.setdefaulttimeout(None)

        if feed.bozo and not feed.entries:
            return {"ok": False, "error": str(feed.bozo_exception)}

        recent = 0
        articles = []
        for entry in feed.entries:
            parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            if parsed:
                pub_date = datetime(*parsed[:6], tzinfo=timezone.utc)
                is_recent = pub_date >= cutoff_time
                if is_recent:
                    recent += 1
                articles.append({
                    "title": entry.get("title", "(no title)"),
                    "link": entry.get("link", ""),
                    "date": pub_date.strftime("%m-%d %H:%M"),
                    "recent": is_recent,
                })
            else:
                articles.append({
                    "title": entry.get("title", "(no title)"),
                    "link": entry.get("link", ""),
                    "date": "??-?? ??:??",
                    "recent": False,
                })

        return {
            "ok": True,
            "title": feed.feed.get("title", "(no title)"),
            "total": len(feed.entries),
            "recent": recent,
            "articles": articles,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    print(f"Testing RSS feeds (last {HOURS}h cutoff: {cutoff_time.strftime('%Y-%m-%d %H:%M')} UTC)\n")

    total_feeds = 0
    failed_feeds = 0

    for category, urls in RSS_SOURCES.items():
        print(f"── {category}")
        for url in urls:
            total_feeds += 1
            result = test_feed(url)
            if result["ok"]:
                print(f"   ✅  {result['title']}")
                print(f"       {result['recent']} recent / {result['total']} total  ({url})")
                for art in result["articles"]:
                    flag = "🆕" if art["recent"] else "  "
                    print(f"       {flag} [{art['date']}] {art['title']}")
                    print(f"              {art['link']}")
            else:
                failed_feeds += 1
                print(f"   ❌  {url}")
                print(f"       Error: {result['error']}")
        print()

    print(f"Result: {total_feeds - failed_feeds}/{total_feeds} feeds OK")


if __name__ == "__main__":
    main()
