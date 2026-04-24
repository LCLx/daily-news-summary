import os
from dotenv import load_dotenv

load_dotenv()

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
}

# US stock market feeds — fed to Claude for market_pulse narrative only,
# not rendered as regular news items.
STOCK_RSS_FEEDS = [
    'https://feeds.marketwatch.com/marketwatch/marketpulse/',
    'https://feeds.marketwatch.com/marketwatch/topstories/',
    'https://news.google.com/rss/search?q=when:24h+%22stock+market%22+OR+%22S%26P+500%22+OR+%22Nasdaq%22&hl=en-US&gl=US&ceid=US:en',
]

# US index symbols (CNBC quote API) + display metadata.
# `unit` controls how change is rendered: 'pct' uses CNBC's change_pct string
# (e.g. '-0.41%'); 'bp' converts yield change in percentage points to
# basis points (e.g. '+3bp').
STOCK_INDICES = [
    {'symbol': '.SPX', 'name': 'S&P 500', 'unit': 'pct'},
    {'symbol': '.IXIC', 'name': 'Nasdaq', 'unit': 'pct'},
    {'symbol': '.DJI', 'name': 'Dow Jones', 'unit': 'pct'},
    {'symbol': '.VIX', 'name': 'VIX', 'unit': 'pct'},
    {'symbol': 'US10Y', 'name': '10Y Treasury', 'unit': 'bp'},
]

# LLM backend
BACKEND = (os.environ.get('BACKEND') or '').strip().upper()
MODEL = os.environ.get('MODEL')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
AWS_REGION = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or 'us-east-1'
MAX_TOKENS = 8000
MAX_RETRIES = 2

DEFAULT_CLAUDE_API_MODEL = 'claude-haiku-4-5-20251001'
DEFAULT_BEDROCK_CLAUDE_MODEL = 'global.anthropic.claude-haiku-4-5-20251001-v1:0'
DEFAULT_CLAUDE_CLI_MODEL = 'haiku'
DEFAULT_CODEX_CLI_MODEL = 'gpt-5.4-mini'

# Gmail API (OAuth2)
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_CLIENT_ID = os.environ.get('GMAIL_CLIENT_ID')
GMAIL_CLIENT_SECRET = os.environ.get('GMAIL_CLIENT_SECRET')
GMAIL_REFRESH_TOKEN = os.environ.get('GMAIL_REFRESH_TOKEN')
EMAIL_TO = os.environ.get('EMAIL_TO')
# Legacy SMTP (still supported as fallback)
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')

# Chinese category name → emoji fallback (used by digest.py)
CATEGORY_EMOJIS = {
    '科技与AI': '💻', '国际政治': '🌍', '经济与商业': '💰',
    '太平洋西北地区': '🌲', '健康与科学': '🔬',
}

# Chinese category name → English RSS key (used by digest.py to resolve number-only refs)
CATEGORY_ZH_TO_RSS = {
    '科技与AI': 'Tech & AI', '国际政治': 'Global Affairs', '经济与商业': 'Business & Finance',
    '太平洋西北地区': 'Pacific Northwest', '健康与科学': 'Health & Science',
}
