import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

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
        'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
    ],
    'Business & Finance': [
        'https://www.ft.com/rss/home',
        'https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com+business&ceid=US:en&hl=en-US&gl=US',
        'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
    ],
    'Pacific Northwest': [
        'https://www.seattletimes.com/seattle-news/feed/',
        'https://www.cbc.ca/webfeed/rss/rss-canada-britishcolumbia',
    ],
    'Health & Science': [
        'https://www.sciencedaily.com/rss/all.xml',
        'https://www.nature.com/nature.rss',
        'https://feeds.npr.org/1007/rss.xml',
    ],
    'Deals': [
        'https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1',
        'https://www.reddit.com/r/deals.rss',
    ],
}

# Claude model
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
CLAUDE_MODEL = os.environ.get('CLAUDE_MODEL', 'claude-haiku-4-5-20251001')
CLAUDE_MAX_TOKENS = 8000
CLAUDE_MAX_RETRIES = 2

# Gmail SMTP
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
EMAIL_TO = os.environ.get('EMAIL_TO')

# Chinese category name → emoji fallback (used by digest.py)
CATEGORY_EMOJIS = {
    '科技与AI': '💻', '国际政治': '🌍', '经济与商业': '💰',
    '太平洋西北地区': '🌲', '健康与科学': '🔬', '今日优惠': '🛍️',
}
