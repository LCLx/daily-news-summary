#!/usr/bin/env python3
"""
Daily news digest generator
Uses RSS + Claude API + Resend email
"""

import os
import re
import socket
import feedparser
import markdown as md
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
}

# Claude API configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
CLAUDE_MODEL = os.environ.get('CLAUDE_MODEL', 'claude-haiku-4-5-20251001')

# Gmail SMTP configuration
GMAIL_USER = os.environ.get('GMAIL_USER')        # your.address@gmail.com
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')  # 16-char App Password
EMAIL_TO = os.environ.get('EMAIL_TO')            # Recipients, comma-separated

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

    # 1. media:thumbnail (BBC, Ars Technica)
    thumbnails = getattr(entry, 'media_thumbnail', None)
    if thumbnails:
        url = thumbnails[0].get('url')
        if is_valid_image_url(url):
            return url

    # 2. media:content (Guardian, Ars Technica) — last item tends to be largest
    media = getattr(entry, 'media_content', None)
    if media:
        url = media[-1].get('url', '')
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


def fetch_rss_articles(category, feeds, hours=24):
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
                if feed_article_count >= 4:  # Max 4 articles per feed
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
    Generate a Chinese digest using the Claude API.

    Args:
        all_articles: dict of articles grouped by category

    Returns:
        str: Generated Chinese digest in markdown
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

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

    # Claude prompt
    prompt = f"""以下是今日各板块的英文新闻（已按板块分类）：

{full_content}

请按以下要求生成中文新闻摘要：

**输出要求：**
1. 分为5个板块：科技与AI、国际政治、经济与商业、太平洋西北地区、健康与科学
2. 每个板块选出最重要的5条新闻
3. 每条新闻包含：
   - 中文标题
   - 100-150字中文摘要
   - 原文链接（保持原样）
   - 来源媒体名称

**格式示例：**
## 💻 科技与AI

### 1. [中文标题]
![](图片URL)
[中文摘要，100-150字]

🔗 原文: [原始英文标题](链接)
📰 来源: 媒体名称 | 发布时间

---

### 2. [中文标题]
...

**重要：**
- 不要使用任何citation标签（如<cite>）
- 链接使用标准markdown格式
- 选择最有新闻价值和影响力的内容
- 摘要要准确、客观、简洁
- 直接输出内容，不要有任何开场白或结束语
- 如果文章提供了"图片"字段，在中文标题下一行插入 ![](图片URL)；没有"图片"字段则**绝对不能**插入任何图片，不要自行补充或猜测图片URL

**选稿标准：**
- 优先选影响全球格局的重大事件，避免软新闻和娱乐性内容
- 同一事件只选一条，选报道最完整的
- 科技板块优先选 AI 相关新闻
"""

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    print("Calling Claude API to generate digest...")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=10000,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    return message.content[0].text


def build_email_html(body_markdown):
    """
    Render markdown to a complete HTML email using the markdown library.

    Args:
        body_markdown: Email body in markdown format

    Returns:
        str: Full HTML document string
    """
    body_html = md.markdown(body_markdown, extensions=['extra'])
    # Hide broken images (hotlink-blocked or expired URLs) instead of showing broken icon
    body_html = body_html.replace('<img ', '<img onerror="this.style.display=\'none\'" ')

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
      }}
      p {{
        margin: 15px 0;
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


def send_email_gmail(subject, body_markdown, recipients):
    """
    Send an HTML email via Gmail SMTP using an App Password.

    Args:
        subject: Email subject line
        body_markdown: Email body in markdown format
        recipients: List of recipient addresses
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("⚠️ GMAIL_USER or GMAIL_APP_PASSWORD not set, skipping email")
        return

    html = build_email_html(body_markdown)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = ', '.join(recipients)
    msg.attach(MIMEText(html, 'html'))

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
        articles = fetch_rss_articles(category, feeds)
        all_articles[category] = articles
        print(f"    {len(articles)} recent articles")

    total_articles = sum(len(articles) for articles in all_articles.values())
    print(f"\n✅ {total_articles} articles fetched\n")

    if total_articles == 0:
        print("⚠️ No articles found, exiting")
        return

    # 2. Generate digest via Claude
    summary = generate_summary_with_claude(all_articles)

    # 3. Print to console
    print("\n" + "=" * 60)
    print("📋 Generated digest:")
    print("=" * 60)
    print(summary)
    print("=" * 60)

    # 4. Send email
    if EMAIL_TO:
        recipients = [email.strip() for email in EMAIL_TO.split(',')]
        subject = f"📰 每日新闻摘要 - {datetime.now().strftime('%Y年%m月%d日')}"
        send_email_gmail(subject, summary, recipients)
    else:
        print("\n⚠️ EMAIL_TO not set, skipping email")

    print("\n✅ Done!")


if __name__ == '__main__':
    main()
