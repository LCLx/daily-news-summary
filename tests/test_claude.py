#!/usr/bin/env python3
"""
Test Claude API output with real RSS articles, skipping email sending.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from email_pipeline import RSS_SOURCES, fetch_rss_articles, generate_summary_with_claude, build_email_html

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated')
os.makedirs(OUTPUT_DIR, exist_ok=True)

SIMPLE_MODE = os.environ.get('MODE', '').upper() == 'TEST'

if __name__ == '__main__':
    if SIMPLE_MODE:
        print("⚡ TEST mode: using 1 feed per category\n")
    print("📥 Fetching real RSS articles...\n")
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
    print(f"\nTotal: {total} articles\n")

    if total == 0:
        print("No articles found, exiting.")
        exit(1)

    print("Invoking Claude...\n" + "=" * 60 + "\n")
    result = generate_summary_with_claude(all_articles)
    print(result)

    html = build_email_html(result)
    preview_path = os.path.join(OUTPUT_DIR, "preview.html")
    with open(preview_path, "w") as f:
        f.write(html)
    print(f"\nHTML preview saved to {preview_path}")
