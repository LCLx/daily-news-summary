from core.llm_client import _strip_fences


class TestStripFences:
    def test_json_fences_stripped(self):
        text = '```json\n{"sections": []}\n```'
        assert _strip_fences(text) == '{"sections": []}'

    def test_plain_fences_stripped(self):
        text = '```\n{"sections": []}\n```'
        assert _strip_fences(text) == '{"sections": []}'

    def test_no_fences_unchanged(self):
        text = '{"sections": []}'
        assert _strip_fences(text) == '{"sections": []}'

    def test_fences_with_language_identifier(self):
        text = '```python\nprint("hello")\n```'
        assert _strip_fences(text) == 'print("hello")'
