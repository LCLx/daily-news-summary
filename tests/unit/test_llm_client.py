import json
from pathlib import Path

from core import llm_client


def test_parse_digest_text_repairs_and_normalizes():
    text = '[{"category": "科技与AI", "items": []}]'

    assert json.loads(llm_client._parse_digest_text(text, 'test')) == {
        'sections': [{'category': '科技与AI', 'items': []}],
    }


def test_call_codex_cli_uses_exec_output_file(monkeypatch):
    seen = {}

    class Result:
        returncode = 0
        stdout = ''
        stderr = ''

    def fake_which(name):
        return '/usr/local/bin/codex' if name == 'codex' else None

    def fake_run(command, **kwargs):
        seen['command'] = command
        seen['kwargs'] = kwargs
        output_path = Path(command[command.index('--output-last-message') + 1])
        output_path.write_text('{"sections": []}', encoding='utf-8')
        return Result()

    monkeypatch.setattr(llm_client.shutil, 'which', fake_which)
    monkeypatch.setattr(llm_client.subprocess, 'run', fake_run)

    assert llm_client._call_codex_cli('生成摘要', 'gpt-test') == '{"sections": []}'

    command = seen['command']
    assert command[:2] == ['/usr/local/bin/codex', 'exec']
    assert '--ephemeral' in command
    assert command[command.index('--sandbox') + 1] == 'read-only'
    assert command[command.index('--model') + 1] == 'gpt-test'
    assert command[-1].startswith('你是一个文本摘要后端。')
    assert seen['kwargs']['stdin'] is llm_client.subprocess.DEVNULL
