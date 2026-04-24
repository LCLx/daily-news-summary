import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from anthropic import Anthropic, APIStatusError
from json_repair import repair_json

from core.config import (
    ANTHROPIC_API_KEY,
    AWS_REGION,
    BACKEND,
    DEFAULT_BEDROCK_CLAUDE_MODEL,
    DEFAULT_CLAUDE_API_MODEL,
    DEFAULT_CLAUDE_CLI_MODEL,
    MAX_RETRIES,
    MAX_TOKENS,
    MODEL,
)

_PROMPT_PATH = Path(__file__).parent.parent / 'prompts' / 'email_digest.md'

_FORMAT_INSTRUCTIONS = """输出一个 JSON 对象，不要任何其他内容（无 markdown、无开场白、无结束语）。

**JSON 格式：**
{
  "sections": [
    {"category": "科技与AI", "items": [
      {"ref": "3", "title_zh": "中文标题", "summary_zh": "100-150字中文摘要"}
    ]}
  ],
  "market_pulse": {
    "summary": "2-3 句定调",
    "drivers": [{"title": "驱动名", "detail": "30-60字详情"}],
    "watch": ["前瞻1", "前瞻2"],
    "refs": ["1", "3"]
  }
}

market_pulse 引用的是"股市"板块的文章编号。若股市素材不足，整个 market_pulse 设为 null。
只输出合法 JSON，不要任何其他内容。"""


def _normalize_digest(data):
    """Wrap bare list into {"sections": [...]} if the backend omitted the wrapper."""
    if isinstance(data, list):
        return {'sections': data}
    return data


def _validate_digest_structure(data):
    """Validate that the backend output matches the expected digest schema.

    Raises ValueError if the structure is malformed (triggers retry).
    market_pulse is optional and may be null; validated lightly if present.
    """
    if not isinstance(data, dict) or 'sections' not in data:
        raise ValueError(f"Expected dict with 'sections' key, got {type(data).__name__}")
    sections = data['sections']
    if not isinstance(sections, list):
        raise ValueError(f"Expected 'sections' to be a list, got {type(sections).__name__}")
    for i, section in enumerate(sections):
        if not isinstance(section, dict):
            raise ValueError(f"sections[{i}] is {type(section).__name__}, expected dict")
        if 'category' not in section or 'items' not in section:
            raise ValueError(f"sections[{i}] missing required keys (has: {list(section.keys())})")

    pulse = data.get('market_pulse')
    if pulse is not None and not isinstance(pulse, dict):
        raise ValueError(f"market_pulse must be dict or null, got {type(pulse).__name__}")


def generate_summary(all_articles, stock_articles=None, stock_snapshot=''):
    """
    Generate a Chinese digest via the configured LLM backend.

    Backend selection:
      BACKEND=BEDROCK_CLAUDE → Claude via AWS Bedrock
      BACKEND=CLAUDE_API  → Anthropic API
      BACKEND=CLAUDE_CLI  → Claude CLI subprocess (local dev / subscription)
      BACKEND=CODEX_CLI   → Codex CLI subprocess (local dev / subscription)

    Args:
        all_articles: dict of articles grouped by narrative category name
        stock_articles: list of stock-market articles (fed to market_pulse only)
        stock_snapshot: pre-formatted compact index snapshot string

    Returns:
        str: JSON string with "sections" key and optional "market_pulse"
    """
    prompt = _build_prompt(all_articles, stock_articles or [], stock_snapshot)

    if BACKEND == 'CLAUDE_API':
        if not ANTHROPIC_API_KEY:
            raise ValueError("Set ANTHROPIC_API_KEY for BACKEND=CLAUDE_API")
        model = _model_for_backend(BACKEND)
        print(f"Calling Claude API to generate digest... (model: {model})")
        return _call_claude_api(prompt, model)
    if BACKEND == 'BEDROCK_CLAUDE':
        model = _model_for_backend(BACKEND)
        print(f"Calling Bedrock Claude to generate digest... (model: {model}, region: {AWS_REGION})")
        return _call_bedrock_claude(prompt, model)
    if BACKEND == 'CLAUDE_CLI':
        model = _model_for_backend(BACKEND)
        print(f"Calling Claude CLI to generate digest... (model: {model})")
        return _call_claude_cli(prompt, model)
    if BACKEND == 'CODEX_CLI':
        model = _model_for_backend(BACKEND)
        model_label = model or 'codex default'
        print(f"Calling Codex CLI to generate digest... (model: {model_label})")
        return _call_codex_cli(prompt, model)
    raise ValueError(
        f"Unsupported BACKEND={BACKEND!r}. "
        "Expected CLAUDE_API, BEDROCK_CLAUDE, CLAUDE_CLI, or CODEX_CLI"
    )


def _model_for_backend(backend):
    if MODEL:
        return MODEL
    if backend == 'CLAUDE_API':
        return DEFAULT_CLAUDE_API_MODEL
    if backend == 'BEDROCK_CLAUDE':
        return DEFAULT_BEDROCK_CLAUDE_MODEL
    if backend == 'CLAUDE_CLI':
        return DEFAULT_CLAUDE_CLI_MODEL
    if backend == 'CODEX_CLI':
        return None
    return MODEL


def _parse_digest_text(text, source_name):
    text = _strip_fences(text.strip())
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        text = repair_json(text, ensure_ascii=False)
        parsed = json.loads(text)
        print("✅ JSON repaired")
    parsed = _normalize_digest(parsed)
    try:
        _validate_digest_structure(parsed)
    except ValueError:
        print(f"⚠️ Raw {source_name} output (first 500 chars):\n{text[:500]}")
        raise
    return json.dumps(parsed, ensure_ascii=False)


def _call_claude_api(prompt, model):
    """Call Anthropic API with plain text output + json_repair fallback."""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    def call():
        message = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_digest_text(message.content[0].text, 'Claude API')

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return call()
        except APIStatusError as e:
            last_err = e
            print(f"⚠️ API attempt {attempt}/{MAX_RETRIES} failed — "
                  f"HTTP {e.status_code} | {type(e).__name__}: {e.message}"
                  f"{f' | request_id: {e.request_id}' if e.request_id else ''}")
        except Exception as e:
            last_err = e
            print(f"⚠️ API attempt {attempt}/{MAX_RETRIES} failed — "
                  f"{type(e).__name__}: {e}")
    raise RuntimeError(f"Claude API failed after {MAX_RETRIES} attempts: {last_err}") from last_err


def _call_bedrock_claude(prompt, model):
    """Call Claude through AWS Bedrock with plain text output + json_repair fallback."""
    client = boto3.client('bedrock-runtime', region_name=AWS_REGION)

    def call():
        request_body = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': MAX_TOKENS,
            'messages': [
                {
                    'role': 'user',
                    'content': [{'type': 'text', 'text': prompt}],
                },
            ],
        }
        response = client.invoke_model(
            modelId=model,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json',
        )
        payload = json.loads(response['body'].read())
        text = ''.join(
            block.get('text', '')
            for block in payload.get('content', [])
            if isinstance(block, dict)
        )
        if not text.strip():
            raise RuntimeError("Bedrock Claude returned empty output")
        return _parse_digest_text(text, 'Bedrock Claude')

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return call()
        except ClientError as e:
            last_err = e
            error = e.response.get('Error', {})
            print(f"⚠️ Bedrock attempt {attempt}/{MAX_RETRIES} failed — "
                  f"{error.get('Code', type(e).__name__)}: {error.get('Message', e)}")
        except Exception as e:
            last_err = e
            print(f"⚠️ Bedrock attempt {attempt}/{MAX_RETRIES} failed — "
                  f"{type(e).__name__}: {e}")
    raise RuntimeError(f"Bedrock Claude failed after {MAX_RETRIES} attempts: {last_err}") from last_err


def _call_claude_cli(prompt, model):
    """Call Claude CLI with retry + json_repair fallback."""
    claude_bin = shutil.which('claude') or 'claude'
    env = {k: v for k, v in os.environ.items() if k not in ('CLAUDECODE', 'ANTHROPIC_API_KEY')}
    env['MAX_THINKING_TOKENS'] = '0'

    def call():
        result = subprocess.run(
            [claude_bin, '--model', model, '--print', prompt],
            capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise RuntimeError(
                f"Claude CLI failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return _parse_digest_text(result.stdout, 'Claude CLI')

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return call()
        except (RuntimeError, json.JSONDecodeError, ValueError) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                print(f"⚠️ Attempt {attempt} failed ({e}), retrying...")
    raise ValueError(f"Claude CLI failed after {MAX_RETRIES} attempts: {last_err}")


def _call_codex_cli(prompt, model):
    """Call Codex CLI with retry + json_repair fallback."""
    codex_bin = shutil.which('codex') or 'codex'

    def call():
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'codex_output.txt'
            command = [
                codex_bin,
                'exec',
                '--ephemeral',
                '--sandbox',
                'read-only',
                '--color',
                'never',
                '--output-last-message',
                str(output_path),
            ]
            if model:
                command.extend(['--model', model])
            command.append(_wrap_codex_prompt(prompt))

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Codex CLI failed (exit {result.returncode}): {result.stderr.strip()}"
                )
            if output_path.exists() and output_path.read_text(encoding='utf-8').strip():
                text = output_path.read_text(encoding='utf-8')
            else:
                text = result.stdout
            if not text.strip():
                raise RuntimeError("Codex CLI returned empty output")
            return _parse_digest_text(text, 'Codex CLI')

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return call()
        except (RuntimeError, json.JSONDecodeError, ValueError) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                print(f"⚠️ Attempt {attempt} failed ({e}), retrying...")
    raise ValueError(f"Codex CLI failed after {MAX_RETRIES} attempts: {last_err}")


def _wrap_codex_prompt(prompt):
    return (
        "你是一个文本摘要后端。不要读取或修改本地文件，不要运行命令，不要解释过程。"
        "只根据下面输入生成最终 JSON。\n\n"
        f"{prompt}"
    )


def _build_prompt(all_articles, stock_articles, stock_snapshot):
    articles_by_category = []
    for category, articles in all_articles.items():
        if not articles:
            continue
        block = f"\n## {category}\n\n"
        for i, article in enumerate(articles[:15], 1):
            block += f"[{i}] {article['title']} | src: {article['source']}\n{article['summary']}\n\n"
        articles_by_category.append(block)

    full_content = "\n".join(articles_by_category)
    stock_block = _format_stock_block(stock_articles, stock_snapshot)

    template = _PROMPT_PATH.read_text(encoding='utf-8')
    return (
        template
        .replace('$articles', full_content)
        .replace('$stock_block', stock_block)
        .replace('$format_instructions', _FORMAT_INSTRUCTIONS)
    )


def _format_stock_block(stock_articles, stock_snapshot):
    """Format stock articles + index snapshot as a single block for market_pulse input."""
    if not stock_articles and not stock_snapshot:
        return '(今日无股市数据，market_pulse 设为 null)'

    parts = []
    if stock_articles:
        parts.append('## 股市（基于此板块生成 market_pulse）\n')
        for i, article in enumerate(stock_articles[:20], 1):
            parts.append(
                f"[{i}] {article['title']} | src: {article['source']}\n"
                f"{article['summary']}\n"
            )
    if stock_snapshot:
        parts.append('\n## 今日美股指数快照\n')
        parts.append(stock_snapshot)
    return '\n'.join(parts)


def _strip_fences(text):
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    # Strip any preamble before the actual JSON payload.
    stripped = text.lstrip()
    if stripped.startswith(('{', '[')):
        return stripped
    positions = [pos for pos in (text.find('{'), text.find('[')) if pos >= 0]
    if positions:
        text = text[min(positions):]
    return text
