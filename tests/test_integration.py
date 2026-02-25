#!/usr/bin/env python3
"""
Integration test: runs the full pipeline end-to-end.
Fetches RSS → generates Claude digest → sends email → saves HTML preview.
Equivalent to manually triggering the GitHub Actions workflow.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
from core.config import RSS_SOURCES, EMAIL_TO
from core.rss import fetch_rss_articles
from core.claude_client import generate_summary_with_claude
from core.digest import resolve_references
from core.renderer import build_email_html_from_json
from core.mailer import send_email_gmail
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
    json_str = generate_summary_with_claude(all_articles)
    parsed = json.loads(json_str)
    sections = resolve_references(parsed, all_articles)
    print("  Done.")

    # Save JSON and HTML preview
    json_path = os.path.join(OUTPUT_DIR, "preview.json")
    with open(json_path, "w") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)
    print(f"  JSON saved → {json_path}")

    html = build_email_html_from_json(sections)
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
        send_email_gmail(subject, html, recipients)

    print("\n" + "=" * 60)
    print("✅ Integration test complete")
    print("=" * 60)

if __name__ == '__main__':
    run()
