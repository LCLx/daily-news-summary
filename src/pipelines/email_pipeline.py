#!/usr/bin/env python3
"""
Daily news digest: RSS → configured LLM backend → HTML email via Gmail SMTP.
Runs on GitHub Actions daily at 08:00 PST (UTC 16:00).
"""

import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from datetime import datetime

from core.config import RSS_SOURCES, STOCK_RSS_FEEDS, EMAIL_TO
from core.rss import fetch_rss_articles
from core.llm_client import generate_summary
from core.digest import resolve_references, resolve_market_pulse
from core.renderer import build_email_html_from_json
from core.mailer import send_email_gmail, delete_sent_emails
from core.gas_prices import fetch_all_gas_prices
from core.stock_market import fetch_stock_indices, format_snapshot_for_prompt

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'generated')
SIMPLE_MODE = os.environ.get('MODE', '').upper() == 'TEST'


def generate_digest():
    """
    Fetch RSS + gas prices, summarize with the configured LLM backend, render HTML.

    Returns:
        (email_html, parsed_json) or (None, None) if no articles found.
    """
    print("=" * 60)
    print("📰 Daily News Digest")
    if SIMPLE_MODE:
        print("⚡ TEST mode: 1 article per category")
    print("=" * 60)
    print()

    # 1. Fetch narrative-category RSS articles
    print("📥 Fetching RSS articles...")
    all_articles = {}
    for category, feeds in RSS_SOURCES.items():
        print(f"  - {category}...")
        articles = fetch_rss_articles(category, feeds)
        all_articles[category] = articles
        print(f"    {len(articles)} recent articles")

    # 1b. Fetch stock-market RSS (separate — feeds market_pulse only)
    print("  - Stock Market (market_pulse input)...")
    stock_articles = fetch_rss_articles('Stock Market', STOCK_RSS_FEEDS)
    print(f"    {len(stock_articles)} recent articles")

    if SIMPLE_MODE:
        all_articles = {k: v[:1] for k, v in all_articles.items()}
        stock_articles = stock_articles[:3]

    total_articles = sum(len(a) for a in all_articles.values())
    print(f"\n✅ {total_articles} narrative + {len(stock_articles)} stock articles fetched\n")

    if total_articles == 0:
        print("⚠️ No articles found, exiting")
        return None, None

    # 2. Fetch gas prices
    print("⛽ Fetching gas prices...")
    gas_prices = fetch_all_gas_prices()
    for gp in gas_prices:
        print(f"  {gp['city']}: {gp['fuels'][0]['price']} {gp['unit']}")
    if not gas_prices:
        print("  ⚠️ Gas prices unavailable, skipping")

    # 3. Fetch stock index snapshot
    print("📈 Fetching stock indices...")
    stock_indices = fetch_stock_indices()
    for i in stock_indices:
        print(f"  {i['name']}: {i['price']} ({i['change_display']})")
    if not stock_indices:
        print("  ⚠️ Stock indices unavailable, skipping")

    # 4. Generate digest via configured LLM backend (JSON output with sections + market_pulse)
    stock_snapshot = format_snapshot_for_prompt(stock_indices)
    json_str = generate_summary(
        all_articles,
        stock_articles=stock_articles,
        stock_snapshot=stock_snapshot,
    )
    parsed = json.loads(json_str)
    sections = resolve_references(parsed, all_articles)
    market_pulse = resolve_market_pulse(parsed, stock_articles)

    # 5. Print digest to console
    print("\n" + "=" * 60)
    print("📋 Generated digest:")
    print("=" * 60)
    if market_pulse:
        print(f"\n📈 Market Pulse: {market_pulse.get('summary', '')[:80]}...")
    for section in sections:
        print(f"\n{section['emoji']} {section['category']}")
        for i, item in enumerate(section['items'], 1):
            print(f"  {i}. {item['title_zh']}")
    print("\n" + "=" * 60)

    # 6. Render HTML
    email_html = build_email_html_from_json(
        sections,
        gas_prices=gas_prices,
        stock_indices=stock_indices,
        market_pulse=market_pulse,
    )

    return email_html, parsed


def save_preview(email_html, parsed_json):
    """Save preview files to generated/ directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    json_path = os.path.join(OUTPUT_DIR, "preview.json")
    with open(json_path, "w") as f:
        json.dump(parsed_json, f, ensure_ascii=False, indent=2)
    print(f"\n📄 JSON saved → {json_path}")

    preview_path = os.path.join(OUTPUT_DIR, "preview.html")
    with open(preview_path, "w") as f:
        f.write(email_html)
    print(f"📄 Preview saved → {preview_path}")


def send_email(email_html):
    """Send digest email via Gmail."""
    if EMAIL_TO:
        recipients = [addr.strip() for addr in EMAIL_TO.split(',')]
        subject = f"📰 每日新闻摘要 - {datetime.now().strftime('%Y年%m月%d日')}"
        msg_ids = send_email_gmail(subject, email_html, recipients)
        delete_sent_emails(msg_ids)
    else:
        print("\n⚠️ EMAIL_TO not set, skipping email")


def main():
    email_html, parsed = generate_digest()
    if not email_html:
        return
    save_preview(email_html, parsed)
    send_email(email_html)
    print("\n✅ Done!")


if __name__ == '__main__':
    main()
