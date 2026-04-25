import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from core import rss
from core.rss import extract_image_url, _resolve_source_name, _clean_summary


class _Entry(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc


def _time_tuple(dt):
    return dt.utctimetuple()


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


class TestCleanSummary:
    def test_empty_input(self):
        assert _clean_summary('') == ''
        assert _clean_summary(None) == ''

    def test_strips_tags_with_space_preserves_word_boundary(self):
        # Adjacent block tags must not glue words together.
        assert _clean_summary('<p>Hello</p><p>World</p>') == 'Hello World'

    def test_unescapes_entities(self):
        assert _clean_summary('AT&amp;T and M&amp;S') == 'AT&T and M&S'

    def test_escaped_tags_are_stripped_not_preserved_as_literal(self):
        # Unescape runs before tag strip, so &lt;script&gt; gets cleaned like a real tag.
        assert _clean_summary('safe &lt;script&gt;x&lt;/script&gt; text') == 'safe x text'

    def test_preserves_bare_angle_brackets_in_text(self):
        # Scientific/financial text like "value < 5 and > 3" must survive unescape + strip.
        assert _clean_summary('value &lt; 5 and &gt; 3') == 'value < 5 and > 3'

    def test_collapses_whitespace(self):
        assert _clean_summary('a   b\n\n\tc') == 'a b c'

    def test_truncates_to_max_chars(self):
        raw = 'x' * 500
        assert len(_clean_summary(raw)) == 220

    def test_truncates_after_cleaning(self):
        # HTML-heavy input should not eat into the 220-char budget.
        raw = '<p>' + 'x' * 250 + '</p>'
        assert _clean_summary(raw) == 'x' * 220


class TestFetchRssArticles:
    def test_filters_recent_articles_limits_each_feed_and_sorts_newest_first(self, monkeypatch):
        now = datetime.now(timezone.utc)
        feed_entries = {
            'https://example.com/feed-a.xml': [
                _Entry({
                    'title': 'Newest &amp; Escaped',
                    'link': 'https://example.com/newest',
                    'published_parsed': _time_tuple(now - timedelta(hours=1)),
                    'summary': 'new summary',
                    'media_content': [{'url': 'https://example.com/newest.jpg'}],
                }),
                _Entry({
                    'title': 'Second',
                    'link': 'https://example.com/second',
                    'published_parsed': _time_tuple(now - timedelta(hours=2)),
                    'summary': 'second summary',
                }),
                _Entry({
                    'title': 'Third skipped by per-feed limit',
                    'link': 'https://example.com/third',
                    'published_parsed': _time_tuple(now - timedelta(hours=3)),
                    'summary': 'third summary',
                }),
            ],
            'https://unknown.com/feed-b.xml': [
                _Entry({
                    'title': 'Other Feed',
                    'link': 'https://unknown.com/other',
                    'published_parsed': _time_tuple(now - timedelta(minutes=30)),
                    'summary': 'other summary',
                }),
                _Entry({
                    'title': 'Old skipped',
                    'link': 'https://unknown.com/old',
                    'published_parsed': _time_tuple(now - timedelta(hours=48)),
                    'summary': 'old summary',
                }),
            ],
        }

        def fake_parse(feed_url, agent):
            return SimpleNamespace(
                feed={'title': 'Example Feed'},
                entries=feed_entries[feed_url],
            )

        monkeypatch.setattr(rss.feedparser, 'parse', fake_parse)

        articles = rss.fetch_rss_articles(
            'Tech & AI',
            ['https://example.com/feed-a.xml', 'https://unknown.com/feed-b.xml'],
            hours=24,
            max_per_feed=2,
        )

        assert [a['title'] for a in articles] == [
            'Other Feed',
            'Newest & Escaped',
            'Second',
        ]
        assert articles[1]['image_url'] == 'https://example.com/newest.jpg'
        assert all(a['category'] == 'Tech & AI' for a in articles)
        assert all(a['source'] == 'Example Feed' for a in articles)
        assert 'Third skipped by per-feed limit' not in [a['title'] for a in articles]
        assert 'Old skipped' not in [a['title'] for a in articles]

    def test_uses_updated_parsed_when_published_missing(self, monkeypatch):
        now = datetime.now(timezone.utc)

        def fake_parse(feed_url, agent):
            return SimpleNamespace(
                feed={'title': 'Updated Feed'},
                entries=[_Entry({
                    'title': 'Updated Article',
                    'link': 'https://example.com/updated',
                    'updated_parsed': _time_tuple(now - timedelta(hours=1)),
                    'summary': 'updated summary',
                })],
            )

        monkeypatch.setattr(rss.feedparser, 'parse', fake_parse)

        articles = rss.fetch_rss_articles('Global Affairs', ['https://example.com/feed.xml'])

        assert len(articles) == 1
        assert articles[0]['title'] == 'Updated Article'
        assert articles[0]['published']

    def test_parse_failure_skips_feed(self, monkeypatch, capsys):
        def fake_parse(feed_url, agent):
            raise RuntimeError('boom')

        monkeypatch.setattr(rss.feedparser, 'parse', fake_parse)

        assert rss.fetch_rss_articles('Tech & AI', ['https://example.com/feed.xml']) == []
        assert 'Failed to fetch https://example.com/feed.xml' in capsys.readouterr().out
