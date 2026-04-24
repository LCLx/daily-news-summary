import html
from core.renderer import (
    _render_body,
    _render_gas_section,
    _render_market_pulse_section,
    build_email_html_from_json,
)


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

    def test_includes_market_pulse_before_news(self):
        result = build_email_html_from_json(
            [_make_section()],
            stock_indices=[{
                'name': 'S&P 500',
                'price': '5,000.00',
                'direction': 'up',
                'change_display': '+0.50%',
            }],
            market_pulse={'summary': '市场走强。'},
        )
        assert result.index('股市脉搏') < result.index('科技与AI')
        assert '市场走强。' in result

    def test_includes_gas_prices_after_news(self):
        result = build_email_html_from_json(
            [_make_section()],
            gas_prices=[{
                'city': 'Seattle',
                'fuels': [{
                    'type': 'Regular',
                    'price': '4.123',
                    'change': '+$0.010',
                    'direction': 'up',
                }],
                'source_url': 'https://example.com/gas',
                'source_name': 'AAA',
                'unit': '$/gal',
            }],
        )
        assert result.index('科技与AI') < result.index('油价速览')
        assert 'Seattle' in result


class TestRenderMarketPulse:
    def test_indices_direction_markers(self):
        body = _render_market_pulse_section(
            [
                {
                    'name': 'Nasdaq',
                    'price': '18,000',
                    'direction': 'up',
                    'change_display': '+1.20%',
                },
                {
                    'name': 'Dow',
                    'price': '40,000',
                    'direction': 'down',
                    'change_display': '-0.20%',
                },
                {
                    'name': '10Y Yield',
                    'price': '4.50%',
                    'direction': 'same',
                    'change_display': '0bp',
                },
            ],
            None,
        )

        assert '▲ +1.20%' in body
        assert '▼ -0.20%' in body
        assert '0bp' in body

    def test_pulse_narrative_escapes_user_content_and_related_links(self):
        body = _render_market_pulse_section(
            [],
            {
                'summary': '<script>alert("x")</script>',
                'drivers': [{'title': 'AI & 芯片', 'detail': '<b>上涨</b>'}],
                'watch': ['FOMC & CPI'],
                'related': [{
                    'title': 'Market <Move>',
                    'link': 'https://example.com/?a=1&b=2',
                    'source': '"when:24h allinurl:reuters.com business" - Google News',
                }],
            },
        )

        assert '<script>' not in body
        assert html.escape('<script>alert("x")</script>') in body
        assert html.escape('<b>上涨</b>') in body
        assert 'Google News' in body
        assert 'https://example.com/?a=1&amp;b=2' in body


class TestRenderGasSection:
    def test_gas_section_direction_markers_and_average(self):
        body = _render_gas_section([{
            'city': 'Vancouver',
            'fuels': [
                {'type': 'Regular', 'price': '185.9', 'change': '2¢', 'direction': 'up'},
                {'type': 'Premium', 'price': '205.9', 'change': '1¢', 'direction': 'down'},
                {'type': 'Diesel', 'price': '190.9', 'change': '0¢', 'direction': 'same'},
            ],
            'average_price': '$1.86',
            'source_url': 'https://example.com/gas',
            'source_name': 'Gas Wizard',
            'unit': '¢/L',
            'is_prediction': True,
        }])

        assert '油价速览' in body
        assert "Tomorrow's Prediction" in body
        assert '▲ 2¢' in body
        assert '▼ 1¢' in body
        assert '0¢' in body
        assert '当前均价: $1.86/L' in body
