import json
from io import BytesIO
from pathlib import Path

import pytest

from core import llm_client


def test_parse_digest_text_repairs_and_normalizes():
    text = '[{"category": "科技与AI", "items": []}]'

    assert json.loads(llm_client._parse_digest_text(text, 'test')) == {
        'sections': [{'category': '科技与AI', 'items': []}],
    }


def test_generate_summary_requires_backend(monkeypatch):
    monkeypatch.setattr(llm_client, 'BACKEND', '')

    with pytest.raises(ValueError, match='Set BACKEND'):
        llm_client.generate_summary({})


def test_model_for_codex_cli_defaults_to_mini(monkeypatch):
    monkeypatch.setattr(llm_client, 'MODEL', None)

    assert llm_client._model_for_backend('CODEX_CLI') == 'gpt-5.4-mini'


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


def test_call_bedrock_claude_invokes_messages_api(monkeypatch):
    seen = {}

    class Client:
        def invoke_model(self, **kwargs):
            seen['kwargs'] = kwargs
            return {
                'body': BytesIO(
                    json.dumps({
                        'content': [
                            {'type': 'text', 'text': '{"sections": []}'},
                        ],
                    }).encode('utf-8')
                )
            }

    def fake_client(service_name, **kwargs):
        seen['service_name'] = service_name
        seen['client_kwargs'] = kwargs
        return Client()

    monkeypatch.setattr(llm_client.boto3, 'client', fake_client)
    monkeypatch.setattr(llm_client, 'AWS_REGION', 'us-east-1')

    assert llm_client._call_bedrock_claude('生成摘要', 'bedrock-test-model') == '{"sections": []}'

    assert seen['service_name'] == 'bedrock-runtime'
    assert seen['client_kwargs']['region_name'] == 'us-east-1'
    request = seen['kwargs']
    assert request['modelId'] == 'bedrock-test-model'
    assert request['contentType'] == 'application/json'
    assert request['accept'] == 'application/json'
    body = json.loads(request['body'])
    assert body['anthropic_version'] == 'bedrock-2023-05-31'
    assert body['max_tokens'] == llm_client.MAX_TOKENS
    assert body['messages'] == [
        {'role': 'user', 'content': [{'type': 'text', 'text': '生成摘要'}]},
    ]
