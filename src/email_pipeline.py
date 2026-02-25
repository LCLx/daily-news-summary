#!/usr/bin/env python3
"""
Daily news digest generator
Uses RSS + Claude API + Resend email
"""

import html
import json
import os
import re
import shutil
import socket
import subprocess
import feedparser
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime, timedelta, timezone
from anthropic import Anthropic
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ==================== Configuration ====================

# RSS sources grouped by category
RSS_SOURCES = {
    'Tech & AI': [
        # 'https://techcrunch.com/feed/',
        'https://www.theverge.com/rss/index.xml',
        # 'https://arstechnica.com/feed/',
        'https://www.wired.com/feed/rss',
        'https://www.techmeme.com/feed.xml',
    ],
    'Global Affairs': [
        'https://www.theguardian.com/world/rss',
        'https://feeds.bbci.co.uk/news/world/rss.xml',
        # 'https://www.npr.org/rss/rss.php?id=1004',
        'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',  # NYT Homepage
    ],
    'Business & Finance': [
        'https://www.ft.com/rss/home',
        'https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com+business&ceid=US:en&hl=en-US&gl=US',
        'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',  # WSJ Markets
    ],
    'Pacific Northwest': [
        'https://www.seattletimes.com/seattle-news/feed/',
        'https://www.cbc.ca/webfeed/rss/rss-canada-britishcolumbia',  # CBC BC
    ],
    'Health & Science': [
        'https://www.sciencedaily.com/rss/all.xml',
        'https://www.nature.com/nature.rss',
        'https://feeds.npr.org/1007/rss.xml',  # NPR Health
    ],
    'Deals': [
        'https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1',
        'https://www.reddit.com/r/deals.rss',
    ],
}

# Claude API configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
CLAUDE_MODEL = os.environ.get('CLAUDE_MODEL', 'claude-haiku-4-5-20251001')

# Gmail SMTP configuration
GMAIL_USER = os.environ.get('GMAIL_USER')        # your.address@gmail.com
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')  # 16-char App Password
EMAIL_TO = os.environ.get('EMAIL_TO')            # Recipients, comma-separated

# Category emoji fallback map (used by resolve_references)
CATEGORY_EMOJIS = {
    '科技与AI': '💻', '国际政治': '🌍', '经济与商业': '💰',
    '太平洋西北地区': '🌲', '健康与科学': '🔬', '今日优惠': '🛍️',
}

# ==================== Core functions ====================

def extract_image_url(entry):
    """
    Extract a thumbnail image URL from a feedparser entry.
    Tries fields in priority order; returns None if nothing found.
    """
    def is_valid_image_url(url):
        """Reject favicons, tiny icons, and non-image files."""
        if not url:
            return False
        lower = url.lower()
        # Reject favicon files and known non-article-image domains
        if 'favicon' in lower:
            return False
        if lower.endswith(('.ico', '.svg', '.mp4', '.webm', '.ogg')):
            return False
        # Google News RSS only has the site favicon, not article images
        if url.startswith('https://news.google.com/'):
            return False
        return True

    # 1. media:content (Guardian, Ars Technica) — last item tends to be largest
    media = getattr(entry, 'media_content', None)
    if media:
        url = media[-1].get('url', '')
        if is_valid_image_url(url):
            return url

    # 2. media:thumbnail (BBC, Ars Technica) — fallback, lower resolution
    thumbnails = getattr(entry, 'media_thumbnail', None)
    if thumbnails:
        url = thumbnails[0].get('url')
        if is_valid_image_url(url):
            return url

    # 3. <img> in Atom content (The Verge)
    content = getattr(entry, 'content', None)
    if content:
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content[0].get('value', ''))
        if match and is_valid_image_url(match.group(1)):
            return match.group(1)

    # 4. <img> in summary HTML
    summary = entry.get('summary', '')
    if summary:
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary)
        if match and is_valid_image_url(match.group(1)):
            return match.group(1)

    return None


def fetch_rss_articles(category, feeds, hours=24, max_per_feed=4):
    """
    Fetch recent articles from the given RSS feeds.

    Args:
        category: Section name
        feeds: List of RSS feed URLs
        hours: How many hours back to fetch (default 24)

    Returns:
        list: List of article dicts
    """
    # Use UTC to match the UTC timestamps from feedparser
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = []

    for feed_url in feeds:
        try:
            socket.setdefaulttimeout(15)
            feed = feedparser.parse(feed_url, agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            socket.setdefaulttimeout(None)

            feed_article_count = 0
            for entry in feed.entries:
                if feed_article_count >= max_per_feed:
                    break
                # Parse publish time
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, 'updated_parsed'):
                    pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                else:
                    continue  # Skip entries with no timestamp

                # Only keep articles within the time window
                if pub_date >= cutoff_time:
                    feed_article_count += 1
                    articles.append({
                        'title': entry.title,
                        'link': entry.link,
                        'pub_date': pub_date,  # Keep raw datetime for sorting
                        'published': pub_date.strftime('%Y-%m-%d %H:%M'),
                        'summary': entry.get('summary', '')[:300],
                        'source': feed.feed.get('title', 'Unknown'),
                        'category': category,
                        'image_url': extract_image_url(entry),
                    })
        except Exception as e:
            print(f"⚠️ Failed to fetch {feed_url}: {e}")
            continue

    # Sort by datetime object (newest first)
    articles.sort(key=lambda x: x['pub_date'], reverse=True)
    return articles


def generate_summary_with_claude(all_articles):
    """
    Generate a Chinese digest via Claude API or CLI.

    Backend selection (checked in order):
      1. CLAUDE_BACKEND=cli  → Claude CLI subprocess (local dev / subscription)
      2. ANTHROPIC_API_KEY set → Anthropic API (GitHub Actions / CI)
      3. Neither set          → raises ValueError

    Args:
        all_articles: dict of articles grouped by category

    Returns:
        str: Generated Chinese digest in JSON format
    """
    use_cli = os.environ.get('CLAUDE_BACKEND', '').lower() == 'cli'
    if not use_cli and not ANTHROPIC_API_KEY:
        raise ValueError("Set ANTHROPIC_API_KEY (API) or CLAUDE_BACKEND=cli (CLI)")

    # Build the content block sent to Claude
    articles_by_category = []
    for category, articles in all_articles.items():
        if not articles:
            continue

        category_text = f"\n## {category}\n\n"
        for i, article in enumerate(articles[:15], 1):  # Max 15 articles per category
            category_text += f"[{i}] {article['title']}\n"
            category_text += f"来源: {article['source']}\n"
            category_text += f"时间: {article['published']}\n"
            category_text += f"链接: {article['link']}\n"
            category_text += f"摘要: {article['summary']}\n"
            if article.get('image_url'):
                category_text += f"图片: {article['image_url']}\n"
            category_text += "\n"

        articles_by_category.append(category_text)

    full_content = "\n".join(articles_by_category)

    # Claude prompt — output JSON to minimize output tokens
    prompt = f"""以下是今日各板块的英文新闻（已按板块分类）。每条新闻有编号 [i]，请用 "分类名:编号" 引用。

{full_content}

请从以上新闻中选稿，输出一个 JSON 对象。不要输出任何其他内容（无 markdown、无开场白、无结束语）。

**JSON 格式：**
{{"sections": [
  {{"category": "科技与AI", "emoji": "💻", "items": [
    {{"ref": "Tech & AI:3", "title_zh": "中文标题", "summary_zh": "100-150字中文摘要"}}
  ]}},
  {{"category": "今日优惠", "emoji": "🛍️", "items": [
    {{"ref": "Deals:5", "title_zh": "中文商品名", "summary_zh": "一句话介绍", "price": "$XX.XX", "original_price": "$YY", "discount": "XX%", "store": "Amazon"}}
  ]}}
]}}

**选稿规则：**
- 6个板块：科技与AI、国际政治、经济与商业、太平洋西北地区、健康与科学、今日优惠
- 前5个板块各选最重要的5条新闻
- 今日优惠从 Deals 类别选最多10条
- ref 字段格式为 "分类名:编号"，分类名必须与输入中的板块标题完全一致（如 "Tech & AI:3"）
- summary_zh 长度 100-150 字，准确客观简洁
- 品牌名保留英文原名（如 Logitech、KEF、Garmin、Nintendo）

**选稿标准（新闻）：**
- 优先选影响全球格局的重大事件，避免软新闻和娱乐性内容
- 同一事件只选一条，选报道最完整的
- 科技板块优先选 AI 相关新闻

**今日优惠选品规则：**
- 排除 Renewed/Refurbished/Like-New/Open Box 等二手翻新产品
- 排除母婴产品
- 电子产品/电脑/配件类合计不超过6条，其余名额优先分配给家居、工具、游戏、户外装备、背包箱包等
- 若去掉消耗品后不足10条，可用食品/饮料/日用消耗品补足，消耗品排后面
- 折扣力度优先（30%+优先考虑）
- 如原文有价格信息，必须提取 price/original_price/discount 字段

只输出合法 JSON，不要任何其他内容。"""

    # Set up backend-specific call function
    if use_cli:
        print("Calling Claude CLI to generate digest...")
        claude_bin = shutil.which('claude') or 'claude'
        env = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
        def call_claude():
            result = subprocess.run(
                [claude_bin, '--model', CLAUDE_MODEL, '--print', prompt],
                capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env
            )
            if result.returncode != 0 or not result.stdout.strip():
                raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {result.stderr.strip()}")
            return result.stdout.strip()
    else:
        print("Calling Claude API to generate digest...")
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        def call_claude():
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text

    def strip_fences(text):
        if text.startswith('```'):
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
        return text

    text = strip_fences(call_claude())

    # Validate JSON; retry once if invalid
    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        print(f"⚠️ Claude returned invalid JSON ({e}), retrying...")
        text = strip_fences(call_claude())
        try:
            json.loads(text)
        except json.JSONDecodeError as e2:
            raise ValueError(f"Claude returned invalid JSON twice: {e2}\nOutput: {text[:500]}") from e2

    return text


def resolve_references(parsed_json, all_articles):
    """
    Resolve ref fields in Claude's JSON output to full article data.

    Args:
        parsed_json: Parsed JSON dict from Claude (with "sections" key)
        all_articles: Original article dict keyed by category name

    Returns:
        list of section dicts with resolved article data
    """
    sections = []
    for section in parsed_json.get('sections', []):
        category = section.get('category', '')
        emoji = section.get('emoji') or CATEGORY_EMOJIS.get(category, '')
        resolved_items = []
        for item in section.get('items', []):
            ref = item.get('ref', '')
            if ':' not in ref:
                print(f"⚠️ Invalid ref format: {ref}")
                continue
            cat_key, idx_str = ref.rsplit(':', 1)
            try:
                idx = int(idx_str)
            except ValueError:
                print(f"⚠️ Invalid ref index: {ref}")
                continue
            cat_articles = all_articles.get(cat_key, [])
            if idx < 1 or idx > len(cat_articles):
                print(f"⚠️ Ref out of range: {ref} (have {len(cat_articles)} articles)")
                continue
            original = cat_articles[idx - 1]
            resolved = {
                'title_zh': item.get('title_zh', ''),
                'summary_zh': item.get('summary_zh', ''),
                'link': original.get('link', ''),
                'title': original.get('title', ''),
                'source': original.get('source', ''),
                'published': original.get('published', ''),
                'image_url': original.get('image_url'),
            }
            # Deal-specific fields
            for field in ('price', 'original_price', 'discount', 'store'):
                if field in item:
                    resolved[field] = item[field]
            resolved_items.append(resolved)
        sections.append({
            'category': category,
            'emoji': emoji,
            'items': resolved_items,
        })
    return sections


def build_email_html_from_json(sections):
    """
    Build a complete HTML email directly from resolved section data.

    Args:
        sections: list of section dicts from resolve_references()

    Returns:
        str: Full HTML document string
    """
    article_img_style = (
        'display:block;max-width:100%;height:auto;'
        'margin:10px auto 16px;border-radius:6px;'
    )
    deals_img_style = (
        'width:110px !important;height:110px !important;'
        'max-width:110px !important;max-height:110px !important;'
        'object-fit:contain !important;float:left !important;'
        'margin:0 14px 6px 0 !important;border-radius:4px !important;'
        'border:1px solid #eee !important;background:#f9f9f9 !important;'
    )

    body_parts = []
    for section in sections:
        category = section['category']
        emoji = section.get('emoji', '')
        is_deals = category == '今日优惠'

        body_parts.append(f'<h2>{emoji} {html.escape(category)}</h2>')
        if is_deals:
            body_parts.append('<div class="deals-section">')

        for i, item in enumerate(section['items'], 1):
            body_parts.append(f'<h3>{i}. {html.escape(item["title_zh"])}</h3>')

            # Image — URL goes into an attribute; escape it to prevent attribute injection
            if item.get('image_url'):
                img_style = deals_img_style if is_deals else article_img_style
                body_parts.append(
                    f'<img onerror="this.remove()" style="{img_style}" src="{html.escape(item["image_url"])}" />'
                )

            if is_deals:
                # Price line
                price_parts = []
                if item.get('price'):
                    price_parts.append(f'<strong>{html.escape(item["price"])}</strong>')
                if item.get('original_price') and item.get('discount'):
                    price_parts.append(f'（原价 {html.escape(item["original_price"])}，省 {html.escape(item["discount"])}）')
                if item.get('store'):
                    price_parts.append(f'｜ 📍 {html.escape(item["store"])}')
                if price_parts:
                    body_parts.append(f'<p>{"".join(price_parts)}</p>')
                body_parts.append(f'<p>{html.escape(item["summary_zh"])}</p>')
                body_parts.append(
                    f'<p>🔗 <a href="{html.escape(item["link"])}">查看优惠</a></p>'
                )
            else:
                body_parts.append(f'<p>{html.escape(item["summary_zh"])}</p>')
                body_parts.append(
                    f'<p>🔗 原文: <a href="{html.escape(item["link"])}">{html.escape(item["title"])}</a><br/>'
                    f'📰 来源: {html.escape(item["source"])} | {html.escape(item["published"])}</p>'
                )
            body_parts.append('<hr/>')

        if is_deals:
            body_parts.append('</div>')

    body_html = '\n'.join(body_parts)

    return f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <style>
      body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
        line-height: 1.6;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        color: #333;
      }}
      h2 {{
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 10px;
        margin-top: 30px;
      }}
      h3 {{
        color: #34495e;
        margin-top: 32px;
        margin-bottom: 8px;
        padding-top: 24px;
        border-top: 1px solid #eee;
      }}
      img {{
        display: block !important;
        width: 100% !important;
        max-width: 600px !important;
        height: auto !important;
        max-height: 450px !important;
        border-radius: 6px;
        margin: 10px auto 16px;
      }}
      a {{
        color: #3498db;
        text-decoration: none;
      }}
      a:hover {{
        text-decoration: underline;
      }}
      hr {{
        border: none;
        border-top: 1px solid #eee;
        margin: 25px 0;
        clear: both;
      }}
      p {{
        margin: 15px 0;
      }}
      .deals-section p {{
        white-space: pre-line;
      }}
      .deals-section p strong {{
        font-size: 1.15em;
      }}
      .deals-section img {{
        width: 110px !important;
        height: 110px !important;
        max-width: 110px !important;
        max-height: 110px !important;
        object-fit: contain !important;
        float: left !important;
        margin: 0 14px 6px 0 !important;
        border-radius: 4px !important;
        border: 1px solid #eee !important;
        background: #f9f9f9 !important;
      }}
      .footer {{
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #ddd;
        color: #7f8c8d;
        font-size: 12px;
        text-align: center;
      }}
    </style>
  </head>
  <body>
    <h1 style="color: #2c3e50; text-align: center;">📰 今日新闻摘要</h1>
    <p style="text-align: center; color: #7f8c8d;">{datetime.now().strftime('%Y年%m月%d日')}</p>
    <hr/>
    {body_html}
    <div class="footer">
      由 Claude AI 自动生成<br/>
      <small>Powered by RSS + Claude API</small>
    </div>
  </body>
</html>"""


def send_email_gmail(subject, body_html, recipients):
    """
    Send an HTML email via Gmail SMTP using an App Password.

    Args:
        subject: Email subject line
        body_html: Complete HTML email body
        recipients: List of recipient addresses
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("⚠️ GMAIL_USER or GMAIL_APP_PASSWORD not set, skipping email")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = 'undisclosed-recipients:;'
    msg.attach(MIMEText(body_html, 'html'))

    try:
        print(f"Sending email via Gmail to {', '.join(recipients)}...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipients, msg.as_string())
        print("✅ Email sent.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def main():
    """Main entry point."""
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

    total_articles = sum(len(articles) for articles in all_articles.values())
    print(f"\n✅ {total_articles} articles fetched\n")

    if total_articles == 0:
        print("⚠️ No articles found, exiting")
        return

    # 2. Generate digest via Claude (JSON output)
    json_str = generate_summary_with_claude(all_articles)
    parsed = json.loads(json_str)
    sections = resolve_references(parsed, all_articles)

    # 3. Print to console
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
