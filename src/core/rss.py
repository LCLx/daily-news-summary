import re
import socket
from datetime import datetime, timedelta, timezone

import feedparser


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


_SOURCE_NAME_OVERRIDES = {
    'www.ft.com': 'Financial Times',
}


def _resolve_source_name(feed_url, feed_title):
    """Return a clean source name, handling Google News search and known overrides."""
    from urllib.parse import urlparse
    domain = urlparse(feed_url).hostname or ''
    if domain in _SOURCE_NAME_OVERRIDES:
        return _SOURCE_NAME_OVERRIDES[domain]
    if domain == 'news.google.com' and '/search' in feed_url:
        match = re.search(r'allinurl:([a-zA-Z0-9.-]+\.[a-z]{2,})', feed_url)
        if match:
            return match.group(1).split('.')[0].capitalize()
    return feed_title


def fetch_rss_articles(category, feeds, hours=24, max_per_feed=4):
    """
    Fetch recent articles from the given RSS feeds.

    Args:
        category: Section name
        feeds: List of RSS feed URLs
        hours: How many hours back to fetch (default 24)
        max_per_feed: Max articles to take from each feed

    Returns:
        list: List of article dicts sorted newest first
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = []

    for feed_url in feeds:
        try:
            socket.setdefaulttimeout(15)
            feed = feedparser.parse(
                feed_url,
                agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            )
            socket.setdefaulttimeout(None)

            source_name = _resolve_source_name(feed_url, feed.feed.get('title', 'Unknown'))
            feed_article_count = 0
            for entry in feed.entries:
                if feed_article_count >= max_per_feed:
                    break
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, 'updated_parsed'):
                    pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                else:
                    continue

                if pub_date >= cutoff_time:
                    feed_article_count += 1
                    articles.append({
                        'title': entry.title,
                        'link': entry.link,
                        'pub_date': pub_date,
                        'published': pub_date.strftime('%Y-%m-%d %H:%M'),
                        'summary': entry.get('summary', '')[:300],
                        'source': source_name,
                        'category': category,
                        'image_url': extract_image_url(entry),
                    })
        except Exception as e:
            print(f"⚠️ Failed to fetch {feed_url}: {e}")
            continue

    articles.sort(key=lambda x: x['pub_date'], reverse=True)
    return articles
