#!/usr/bin/env python3
"""
Integration test: runs the full pipeline end-to-end.
Fetches RSS → generates Claude digest → sends email → saves HTML preview.
Equivalent to manually triggering the GitHub Actions workflow.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from email_pipeline import (
    RSS_SOURCES,
    fetch_rss_articles,
    generate_summary_with_claude,
    build_email_html,
    send_email_gmail,
    EMAIL_TO,
)
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated')
os.makedirs(OUTPUT_DIR, exist_ok=True)

SIMPLE_MODE = os.environ.get('MODE', '').upper() == 'TEST'

def run():
    print("=" * 60)
    if SIMPLE_MODE:
        print("🔁 Integration Test — Full Pipeline (TEST mode: 1 feed/category)")
    else:
        print("🔁 Integration Test — Full Pipeline")
    print("=" * 60)

    # Step 1: Fetch RSS
    print("\n[1/3] Fetching RSS articles...")
    all_articles = {}
    for category, feeds in RSS_SOURCES.items():
        kwargs = {'max_per_feed': 15} if category == 'Deals' else {}
        articles = fetch_rss_articles(category, feeds, **kwargs)
        all_articles[category] = articles
        print(f"  {category}: {len(articles)} articles")

    # In TEST mode, limit to 1 article per category to minimize tokens
    if SIMPLE_MODE:
        all_articles = {k: v[:1] for k, v in all_articles.items()}

    total = sum(len(a) for a in all_articles.values())
    print(f"  Total: {total} articles")

    if total == 0:
        print("❌ No articles fetched — check RSS sources or network")
        sys.exit(1)

    # Step 2: Generate digest with Claude
    print("\n[2/3] Generating digest with Claude...")
    summary = generate_summary_with_claude(all_articles)
    print("  Done.")

    # Save HTML preview
    html = build_email_html(summary)
    preview_path = os.path.join(OUTPUT_DIR, "preview.html")
    with open(preview_path, "w") as f:
        f.write(html)
    print(f"  Preview saved → {preview_path}")

    # Step 3: Send email
    print("\n[3/3] Sending email...")
    if not EMAIL_TO:
        print("  ⚠️  EMAIL_TO not set — skipping email send")
    else:
        recipients = [e.strip() for e in EMAIL_TO.split(',')]
        subject = f"📰 每日新闻摘要 - {datetime.now().strftime('%Y年%m月%d日')}"
        send_email_gmail(subject, summary, recipients)

    print("\n" + "=" * 60)
    print("✅ Integration test complete")
    print("=" * 60)

if __name__ == '__main__':
    run()
