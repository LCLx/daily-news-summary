import pytest
from core.claude_client import _validate_digest_structure, _normalize_digest


class TestValidateDigestStructure:
    def test_valid_structure(self):
        data = {'sections': [
            {'category': '科技与AI', 'items': [
                {'ref': '1', 'title_zh': '标题', 'summary_zh': '摘要'},
            ]},
        ]}
        _validate_digest_structure(data)  # should not raise

    def test_empty_sections_valid(self):
        _validate_digest_structure({'sections': []})  # should not raise

    def test_not_a_dict(self):
        with pytest.raises(ValueError, match='Expected dict'):
            _validate_digest_structure('not a dict')

    def test_missing_sections_key(self):
        with pytest.raises(ValueError, match="'sections' key"):
            _validate_digest_structure({'data': []})

    def test_sections_not_list(self):
        with pytest.raises(ValueError, match='to be a list'):
            _validate_digest_structure({'sections': 'not a list'})

    def test_section_is_string(self):
        """The exact Haiku bug: sections contains strings."""
        with pytest.raises(ValueError, match=r'sections\[0\] is str'):
            _validate_digest_structure({'sections': ['科技与AI']})

    def test_section_missing_category(self):
        with pytest.raises(ValueError, match='missing required keys'):
            _validate_digest_structure({'sections': [{'items': []}]})

    def test_section_missing_items(self):
        with pytest.raises(ValueError, match='missing required keys'):
            _validate_digest_structure({'sections': [{'category': '科技与AI'}]})


class TestNormalizeDigest:
    def test_bare_list_wrapped(self):
        """CLI sometimes returns a bare array instead of {"sections": [...]}."""
        data = [{'category': '科技与AI', 'items': []}]
        result = _normalize_digest(data)
        assert result == {'sections': [{'category': '科技与AI', 'items': []}]}

    def test_dict_unchanged(self):
        data = {'sections': [{'category': '科技与AI', 'items': []}]}
        assert _normalize_digest(data) is data

    def test_empty_list_wrapped(self):
        assert _normalize_digest([]) == {'sections': []}
