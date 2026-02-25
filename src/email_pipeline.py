#!/usr/bin/env python3
"""
Daily news digest: RSS → Claude API → HTML email via Gmail SMTP.
Runs on GitHub Actions daily at 08:00 PST (UTC 16:00).
"""

import json
from datetime import datetime

from config import RSS_SOURCES, EMAIL_TO
from rss import fetch_rss_articles
from claude_client import generate_summary_with_claude
from digest import resolve_references
from renderer import build_email_html_from_json
from mailer import send_email_gmail


def main():
    print("=" * 60)
    print("📰 Daily News Digest")
    print("=" * 60)
    print()

    # 1. Fetch all RSS articles
    print("📥 Fetching RSS articles...")
    all_articles = {}
    for category, feeds in RSS_SOURCES.items():
        print(f"  - {category}...")
        kwargs = {'max_per_feed': 15} if category == 'Deals' else {}
        articles = fetch_rss_articles(category, feeds, **kwargs)
        all_articles[category] = articles
        print(f"    {len(articles)} recent articles")

    total_articles = sum(len(a) for a in all_articles.values())
    print(f"\n✅ {total_articles} articles fetched\n")

    if total_articles == 0:
        print("⚠️ No articles found, exiting")
        return

    # 2. Generate digest via Claude (JSON output)
    json_str = generate_summary_with_claude(all_articles)
    sections = resolve_references(json.loads(json_str), all_articles)

    # 3. Print digest to console
    print("\n" + "=" * 60)
    print("📋 Generated digest:")
    print("=" * 60)
    for section in sections:
        print(f"\n{section['emoji']} {section['category']}")
        for i, item in enumerate(section['items'], 1):
            print(f"  {i}. {item['title_zh']}")
    print("\n" + "=" * 60)

    # 4. Build HTML and send email
    email_html = build_email_html_from_json(sections)
    if EMAIL_TO:
        recipients = [addr.strip() for addr in EMAIL_TO.split(',')]
        subject = f"📰 每日新闻摘要 - {datetime.now().strftime('%Y年%m月%d日')}"
        send_email_gmail(subject, email_html, recipients)
    else:
        print("\n⚠️ EMAIL_TO not set, skipping email")

    print("\n✅ Done!")


if __name__ == '__main__':
    main()
