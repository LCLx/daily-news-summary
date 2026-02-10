#!/usr/bin/env python3
"""
Test Claude API output with real RSS articles, skipping email sending.
"""

from dotenv import load_dotenv
load_dotenv()

from daily_news import RSS_SOURCES, fetch_rss_articles, generate_summary_with_claude

if __name__ == '__main__':
    print("📥 Fetching real RSS articles...\n")
    all_articles = {}
    for category, feeds in RSS_SOURCES.items():
        articles = fetch_rss_articles(category, feeds)
        all_articles[category] = articles
        print(f"  {category}: {len(articles)} articles")

    total = sum(len(a) for a in all_articles.values())
    print(f"\nTotal: {total} articles\n")

    if total == 0:
        print("No articles found, exiting.")
        exit(1)

    print("Calling Claude API...\n" + "=" * 60 + "\n")
    result = generate_summary_with_claude(all_articles)
    print(result)
