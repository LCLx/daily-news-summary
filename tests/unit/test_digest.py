import pytest
from core.digest import resolve_references


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
