import pytest
from unittest.mock import MagicMock
from core.rss import extract_image_url, _resolve_source_name


class TestExtractImageUrl:
    def test_media_content(self):
        entry = MagicMock(spec=[])
        entry.media_content = [{'url': 'https://example.com/img.jpg'}]
        assert extract_image_url(entry) == 'https://example.com/img.jpg'

    def test_media_content_picks_last(self):
        entry = MagicMock(spec=[])
        entry.media_content = [
            {'url': 'https://example.com/small.jpg'},
            {'url': 'https://example.com/large.jpg'},
        ]
        assert extract_image_url(entry) == 'https://example.com/large.jpg'

    def test_media_thumbnail(self):
        entry = MagicMock(spec=[])
        entry.media_thumbnail = [{'url': 'https://example.com/thumb.jpg'}]
        entry.get = lambda k, d='': d
        assert extract_image_url(entry) == 'https://example.com/thumb.jpg'

    def test_img_in_content_html(self):
        entry = MagicMock(spec=[])
        entry.content = [{'value': '<p>Text</p><img src="https://example.com/photo.png" />'}]
        entry.get = lambda k, d='': d
        assert extract_image_url(entry) == 'https://example.com/photo.png'

    def test_img_in_summary_html(self):
        entry = MagicMock(spec=[])
        entry.get = lambda k, d='': '<img src="https://example.com/sum.jpg" />' if k == 'summary' else d
        assert extract_image_url(entry) == 'https://example.com/sum.jpg'

    def test_rejects_favicon(self):
        entry = MagicMock(spec=[])
        entry.media_content = [{'url': 'https://example.com/favicon.png'}]
        entry.get = lambda k, d='': d
        assert extract_image_url(entry) is None

    def test_rejects_ico(self):
        entry = MagicMock(spec=[])
        entry.media_content = [{'url': 'https://example.com/icon.ico'}]
        entry.get = lambda k, d='': d
        assert extract_image_url(entry) is None

    def test_rejects_google_news_url(self):
        entry = MagicMock(spec=[])
        entry.media_content = [{'url': 'https://news.google.com/img.jpg'}]
        entry.get = lambda k, d='': d
        assert extract_image_url(entry) is None

    def test_returns_none_when_no_image(self):
        entry = MagicMock(spec=[])
        entry.get = lambda k, d='': d
        assert extract_image_url(entry) is None


class TestResolveSourceName:
    def test_known_override(self):
        assert _resolve_source_name('https://www.ft.com/rss/home', 'FT') == 'Financial Times'

    def test_bbc_override(self):
        assert _resolve_source_name('https://feeds.bbci.co.uk/news/rss.xml', 'BBC') == 'BBC News'

    def test_google_news_search(self):
        url = 'https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com+business'
        result = _resolve_source_name(url, 'Google News')
        assert result == 'Reuters'

    def test_fallback_to_feed_title(self):
        assert _resolve_source_name('https://unknown.com/feed', 'My Blog') == 'My Blog'
