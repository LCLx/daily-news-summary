#!/usr/bin/env python3
"""
Daily news digest generator
Uses RSS + Claude API + Resend email
"""

import os
import feedparser
import markdown as md
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime, timedelta, timezone
from anthropic import Anthropic
import resend

# ==================== Configuration ====================

# RSS sources grouped by category
RSS_SOURCES = {
    '国际政治': [
        'https://www.theguardian.com/world/rss',
        'https://feeds.bbci.co.uk/news/world/rss.xml',
        'https://www.npr.org/rss/rss.php?id=1004',
    ],
    '经济与商业': [
        'https://www.ft.com/rss/home',
        'https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com+business&ceid=US:en&hl=en-US&gl=US',
        'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',  # WSJ Markets
    ],
    '科技与AI': [
        'https://techcrunch.com/feed/',
        'https://www.theverge.com/rss/index.xml',
        'https://arstechnica.com/feed/',
        'https://www.wired.com/feed/rss',
    ],
    '健康与科学': [
        'https://www.sciencedaily.com/rss/all.xml',
        'https://www.nature.com/nature.rss',
        'https://feeds.npr.org/1007/rss.xml',  # NPR Health
    ],
}

# Claude API configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

# Resend email configuration
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
EMAIL_FROM = 'Daily News <onboarding@resend.dev>'  # Free test domain
EMAIL_TO = os.environ.get('EMAIL_TO')  # Recipients, comma-separated

# To use a custom domain:
# EMAIL_FROM = 'Daily News <news@yourdomain.com>'

# ==================== Core functions ====================

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
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                # Parse publish time
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, 'updated_parsed'):
                    pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                else:
                    continue  # Skip entries with no timestamp

                # Only keep articles within the time window
                if pub_date >= cutoff_time:
                    articles.append({
                        'title': entry.title,
                        'link': entry.link,
                        'pub_date': pub_date,  # Keep raw datetime for sorting
                        'published': pub_date.strftime('%Y-%m-%d %H:%M'),
                        'summary': entry.get('summary', '')[:300],
                        'source': feed.feed.get('title', 'Unknown'),
                        'category': category
                    })
        except Exception as e:
            print(f"⚠️ 获取 {feed_url} 失败: {e}")
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
        raise ValueError("请设置 ANTHROPIC_API_KEY 环境变量")

    # Build the content block sent to Claude
    articles_by_category = []
    for category, articles in all_articles.items():
        if not articles:
            continue

        category_text = f"\n## {category}\n\n"
        for i, article in enumerate(articles[:10], 1):  # Max 10 articles per category
            category_text += f"[{i}] {article['title']}\n"
            category_text += f"来源: {article['source']}\n"
            category_text += f"时间: {article['published']}\n"
            category_text += f"链接: {article['link']}\n"
            category_text += f"摘要: {article['summary']}\n\n"

        articles_by_category.append(category_text)

    full_content = "\n".join(articles_by_category)

    # Claude prompt
    prompt = f"""以下是今日各板块的英文新闻（已按板块分类）：

{full_content}

请按以下要求生成中文新闻摘要：

**输出要求：**
1. 分为4个板块：国际政治、经济与商业、科技与AI、健康与科学
2. 每个板块选出最重要的4条新闻
3. 每条新闻包含：
   - 中文标题
   - 100-150字中文摘要
   - 原文链接（保持原样）
   - 来源媒体名称

**格式示例：**
## 🌍 国际政治

### 1. [中文标题]
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
- 直接输出内容，不要有任何开场白或结束语"""

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    print("正在调用Claude API生成摘要...")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8000,
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
        margin-top: 25px;
        margin-bottom: 10px;
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


def send_email_resend(subject, body_markdown, recipients):
    """
    Send an HTML email via Resend.

    Args:
        subject: Email subject line
        body_markdown: Email body in markdown format
        recipients: List of recipient addresses
    """
    if not RESEND_API_KEY:
        print("⚠️ 未设置 RESEND_API_KEY，跳过发送")
        return

    resend.api_key = RESEND_API_KEY

    html = build_email_html(body_markdown)

    try:
        print(f"正在通过Resend发送邮件到 {', '.join(recipients)}...")

        params = {
            "from": EMAIL_FROM,
            "to": recipients,
            "subject": subject,
            "html": html,
        }

        email = resend.Emails.send(params)
        print(f"✅ 邮件发送成功！Email ID: {email.get('id', 'N/A')}")

    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("📰 每日新闻摘要生成器")
    print("=" * 60)
    print()

    # 1. Fetch all RSS articles
    print("📥 正在获取RSS文章...")
    all_articles = {}

    for category, feeds in RSS_SOURCES.items():
        print(f"  - {category}...")
        articles = fetch_rss_articles(category, feeds)
        all_articles[category] = articles
        print(f"    找到 {len(articles)} 篇最新文章")

    total_articles = sum(len(articles) for articles in all_articles.values())
    print(f"\n✅ 共获取 {total_articles} 篇文章\n")

    if total_articles == 0:
        print("⚠️ 没有找到任何新闻，程序退出")
        return

    # 2. Generate digest via Claude
    summary = generate_summary_with_claude(all_articles)

    # 3. Print to console
    print("\n" + "=" * 60)
    print("📋 生成的摘要：")
    print("=" * 60)
    print(summary)
    print("=" * 60)

    # 4. Send email
    if EMAIL_TO:
        recipients = [email.strip() for email in EMAIL_TO.split(',')]
        subject = f"📰 每日新闻摘要 - {datetime.now().strftime('%Y年%m月%d日')}"
        send_email_resend(subject, summary, recipients)
    else:
        print("\n⚠️ 未设置 EMAIL_TO，跳过邮件发送")

    print("\n✅ 完成！")


if __name__ == '__main__':
    main()
