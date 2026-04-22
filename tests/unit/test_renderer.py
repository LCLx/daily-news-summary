import html
from core.renderer import build_email_html_from_json, _render_body


def _make_section(category='科技与AI', emoji='💻', items=None):
    if items is None:
        items = [{
            'title_zh': '测试标题',
            'summary_zh': '测试摘要',
            'link': 'https://example.com/1',
            'title': 'Test Title',
            'source': 'Test Source',
            'published': '2025-01-01 12:00',
            'image_url': 'https://example.com/img.jpg',
        }]
    return {'category': category, 'emoji': emoji, 'items': items}


class TestRenderBody:
    def test_contains_category_and_emoji(self):
        body = _render_body([_make_section()])
        assert '💻' in body
        assert '科技与AI' in body

    def test_contains_title_and_summary(self):
        body = _render_body([_make_section()])
        assert '测试标题' in body
        assert '测试摘要' in body

    def test_contains_link(self):
        body = _render_body([_make_section()])
        assert 'https://example.com/1' in body
        assert '原文' in body

    def test_contains_source(self):
        body = _render_body([_make_section()])
        assert 'Test Source' in body

    def test_image_rendered(self):
        body = _render_body([_make_section()])
        assert 'img' in body
        assert 'https://example.com/img.jpg' in body
        assert 'onerror' in body

    def test_no_image_when_none(self):
        section = _make_section(items=[{
            'title_zh': '无图', 'summary_zh': '摘要',
            'link': 'https://example.com', 'title': 'No Image',
            'source': 'Src', 'published': '2025-01-01', 'image_url': None,
        }])
        body = _render_body([section])
        assert '<img' not in body

    def test_html_escaping(self):
        items = [{
            'title_zh': '<script>alert("xss")</script>',
            'summary_zh': 'Safe & sound "quoted"',
            'link': 'https://example.com', 'title': 'Test',
            'source': 'Src', 'published': '2025-01-01', 'image_url': None,
        }]
        body = _render_body([_make_section(items=items)])
        assert '<script>' not in body
        assert html.escape('<script>alert("xss")</script>') in body

    def test_empty_sections(self):
        body = _render_body([])
        assert body == ''


class TestBuildEmailHtml:
    def test_returns_full_html_document(self):
        result = build_email_html_from_json([_make_section()])
        assert '<!DOCTYPE' in result or '<html' in result
        assert '测试标题' in result

    def test_date_placeholder_replaced(self):
        result = build_email_html_from_json([])
        assert '$date_str' not in result

    def test_body_placeholder_replaced(self):
        result = build_email_html_from_json([])
        assert '$body_html' not in result
