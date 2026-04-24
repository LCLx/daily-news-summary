import pytest
from core.digest import resolve_market_pulse, resolve_references


def _make_articles(category, n):
    """Create n mock articles for a given RSS category."""
    return [
        {
            'title': f'Article {i}',
            'link': f'https://example.com/{i}',
            'source': 'Test Source',
            'published': '2025-01-01 12:00',
            'image_url': f'https://example.com/img{i}.jpg',
        }
        for i in range(1, n + 1)
    ]


@pytest.fixture
def all_articles():
    return {
        'Tech & AI': _make_articles('Tech & AI', 5),
        'Global Affairs': _make_articles('Global Affairs', 3),
    }


class TestResolveReferences:
    def test_valid_refs(self, all_articles):
        parsed = {'sections': [
            {'category': '科技与AI', 'items': [
                {'ref': '1', 'title_zh': '标题一', 'summary_zh': '摘要一'},
                {'ref': '3', 'title_zh': '标题三', 'summary_zh': '摘要三'},
            ]},
        ]}
        sections = resolve_references(parsed, all_articles)
        assert len(sections) == 1
        assert sections[0]['category'] == '科技与AI'
        assert sections[0]['emoji'] == '💻'
        items = sections[0]['items']
        assert len(items) == 2
        assert items[0]['link'] == 'https://example.com/1'
        assert items[0]['title_zh'] == '标题一'
        assert items[1]['link'] == 'https://example.com/3'

    def test_out_of_range_ref_skipped(self, all_articles, capsys):
        parsed = {'sections': [
            {'category': '国际政治', 'items': [
                {'ref': '99', 'title_zh': '标题', 'summary_zh': '摘要'},
            ]},
        ]}
        sections = resolve_references(parsed, all_articles)
        assert len(sections) == 1
        assert len(sections[0]['items']) == 0
        assert 'out of range' in capsys.readouterr().out

    def test_invalid_ref_skipped(self, all_articles, capsys):
        parsed = {'sections': [
            {'category': '科技与AI', 'items': [
                {'ref': 'abc', 'title_zh': '标题', 'summary_zh': '摘要'},
            ]},
        ]}
        sections = resolve_references(parsed, all_articles)
        assert len(sections[0]['items']) == 0
        assert 'Invalid ref' in capsys.readouterr().out

    def test_unknown_category_skipped(self, all_articles, capsys):
        parsed = {'sections': [
            {'category': '不存在的分类', 'items': [
                {'ref': '1', 'title_zh': '标题', 'summary_zh': '摘要'},
            ]},
        ]}
        sections = resolve_references(parsed, all_articles)
        assert len(sections) == 0
        assert 'Unknown category' in capsys.readouterr().out

    def test_malformed_section_skipped(self, all_articles, capsys):
        """The Haiku bug: sections contains strings instead of dicts."""
        parsed = {'sections': ['科技与AI', '国际政治']}
        sections = resolve_references(parsed, all_articles)
        assert len(sections) == 0
        assert 'malformed section' in capsys.readouterr().out.lower()

    def test_legacy_colon_ref_format(self, all_articles):
        parsed = {'sections': [
            {'category': '科技与AI', 'items': [
                {'ref': 'Tech:2', 'title_zh': '标题', 'summary_zh': '摘要'},
            ]},
        ]}
        sections = resolve_references(parsed, all_articles)
        assert sections[0]['items'][0]['link'] == 'https://example.com/2'

    def test_empty_sections(self, all_articles):
        parsed = {'sections': []}
        sections = resolve_references(parsed, all_articles)
        assert sections == []

    def test_missing_sections_key(self, all_articles):
        parsed = {}
        sections = resolve_references(parsed, all_articles)
        assert sections == []


@pytest.fixture
def stock_articles():
    return [
        {
            'title': f'Market Article {i}',
            'link': f'https://markets.example.com/{i}',
            'source': 'Market Source',
        }
        for i in range(1, 4)
    ]


class TestResolveMarketPulse:
    def test_absent_or_null_pulse_returns_none(self, stock_articles):
        assert resolve_market_pulse({}, stock_articles) is None
        assert resolve_market_pulse({'market_pulse': None}, stock_articles) is None
        assert resolve_market_pulse({'market_pulse': 'bad'}, stock_articles) is None

    def test_valid_refs_resolved(self, stock_articles):
        parsed = {
            'market_pulse': {
                'summary': '市场承压。',
                'drivers': [{'title': '利率', 'detail': '收益率上行'}],
                'watch': ['CPI'],
                'refs': ['1', 'Stock:3'],
            }
        }

        pulse = resolve_market_pulse(parsed, stock_articles)

        assert pulse['summary'] == '市场承压。'
        assert pulse['drivers'] == [{'title': '利率', 'detail': '收益率上行'}]
        assert pulse['watch'] == ['CPI']
        assert pulse['related'] == [
            {
                'title': 'Market Article 1',
                'link': 'https://markets.example.com/1',
                'source': 'Market Source',
            },
            {
                'title': 'Market Article 3',
                'link': 'https://markets.example.com/3',
                'source': 'Market Source',
            },
        ]

    def test_bad_refs_skipped_and_bad_lists_filtered(self, stock_articles, capsys):
        parsed = {
            'market_pulse': {
                'summary': '市场震荡。',
                'drivers': [{'title': '财报'}, 'bad'],
                'watch': ['就业数据', {'bad': 'item'}],
                'refs': ['abc', '99', '2'],
            }
        }

        pulse = resolve_market_pulse(parsed, stock_articles)

        assert pulse['drivers'] == [{'title': '财报'}]
        assert pulse['watch'] == ['就业数据']
        assert pulse['related'] == [{
            'title': 'Market Article 2',
            'link': 'https://markets.example.com/2',
            'source': 'Market Source',
        }]
        output = capsys.readouterr().out
        assert 'Invalid market_pulse ref' in output
        assert 'out of range' in output
