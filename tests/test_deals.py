#!/usr/bin/env python3
"""
Quick test: fetch deals from candidate RSS feeds and show raw results.
Run with: uv run tests/test_deals.py
"""

import sys
import os
import socket
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import feedparser
from datetime import datetime, timedelta, timezone

HOURS = 24
cutoff_time = datetime.now(timezone.utc) - timedelta(hours=HOURS)

DEAL_FEEDS = {
    'Slickdeals 首页': 'https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1',
    'Reddit r/deals': 'https://www.reddit.com/r/deals.rss',
    'DealNews': 'https://dealnews.com/rss/',
    'Ben\'s Bargains': 'https://bensbargains.net/feed/',
}

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def fetch_feed(name, url):
    print(f"\n{'='*60}")
    print(f"📦 {name}")
    print(f"   {url}")
    print(f"{'='*60}")

    try:
        socket.setdefaulttimeout(20)
        feed = feedparser.parse(url, agent=UA)
        socket.setdefaulttimeout(None)

        if feed.bozo and not feed.entries:
            print(f"❌ 无法解析: {feed.bozo_exception}")
            return

        feed_title = feed.feed.get('title', '(no title)')
        print(f"Feed 标题: {feed_title}  |  共 {len(feed.entries)} 条")
        print()

        shown = 0
        for entry in feed.entries:
            if shown >= 8:
                break

            parsed = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
            if parsed:
                pub_date = datetime(*parsed[:6], tzinfo=timezone.utc)
                date_str = pub_date.strftime('%m-%d %H:%M')
                is_recent = pub_date >= cutoff_time
                flag = '🆕' if is_recent else '  '
            else:
                date_str = '??-?? ??:??'
                flag = '  '

            title = entry.get('title', '(no title)')
            link = entry.get('link', '')
            summary = entry.get('summary', '')[:150].replace('\n', ' ').strip()

            print(f"{flag} [{date_str}] {title}")
            if summary:
                print(f"         {summary}...")
            print(f"         {link}")
            print()
            shown += 1

    except Exception as e:
        print(f"❌ 异常: {e}")


def main():
    print(f"测试 deals RSS feeds（过去 {HOURS}h，截止 {cutoff_time.strftime('%Y-%m-%d %H:%M')} UTC）")

    for name, url in DEAL_FEEDS.items():
        fetch_feed(name, url)

    print(f"\n{'='*60}")
    print("完成")


if __name__ == '__main__':
    main()
