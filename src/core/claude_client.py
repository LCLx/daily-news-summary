import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from anthropic import Anthropic, APIStatusError
from json_repair import repair_json

from core.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_CLI_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_MAX_RETRIES

_PROMPT_PATH = Path(__file__).parent.parent / 'prompts' / 'email_digest.md'

_FORMAT_INSTRUCTIONS = """输出一个 JSON 对象，不要任何其他内容（无 markdown、无开场白、无结束语）。

**JSON 格式：**
{"sections": [
  {"category": "科技与AI", "items": [
    {"ref": "3", "title_zh": "中文标题", "summary_zh": "100-150字中文摘要"}
  ]},
  {"category": "今日优惠", "items": [
    {"ref": "5", "title_zh": "中文商品名", "summary_zh": "一句话介绍", "price": "$XX.XX", "original_price": "$YY", "discount": "XX%", "store": "Amazon"}
  ]}
]}

只输出合法 JSON，不要任何其他内容。"""


def _normalize_digest(data):
    """Wrap bare list into {"sections": [...]} if Claude omitted the wrapper."""
    if isinstance(data, list):
        return {'sections': data}
    return data


def _validate_digest_structure(data):
    """Validate that Claude's output matches the expected digest schema.

    Raises ValueError if the structure is malformed (triggers retry).
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


def generate_summary_with_claude(all_articles):
    """
    Generate a Chinese digest via Claude API or CLI.

    Backend selection (checked in order):
      1. CLAUDE_BACKEND=cli  → Claude CLI subprocess (local dev / subscription)
      2. ANTHROPIC_API_KEY set → Anthropic API (GitHub Actions / CI)
      3. Neither set          → raises ValueError

    Args:
        all_articles: dict of articles grouped by category name

    Returns:
        str: JSON string with "sections" key
    """
    use_cli = os.environ.get('CLAUDE_BACKEND', '').lower() == 'cli'
    if not use_cli and not ANTHROPIC_API_KEY:
        raise ValueError("Set ANTHROPIC_API_KEY (API) or CLAUDE_BACKEND=cli (CLI)")

    prompt = _build_prompt(all_articles)

    if use_cli:
        print("Calling Claude CLI to generate digest...")
        return _call_cli(prompt)
    else:
        print(f"Calling Claude API to generate digest... (model: {CLAUDE_MODEL})")
        return _call_api(prompt)


def _call_api(prompt):
    """Call Anthropic API with plain text output + json_repair fallback."""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    def call():
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = _strip_fences(message.content[0].text.strip())
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            text = repair_json(text, ensure_ascii=False)
            parsed = json.loads(text)
            print("✅ JSON repaired")
        parsed = _normalize_digest(parsed)
        _validate_digest_structure(parsed)
        return json.dumps(parsed, ensure_ascii=False)

    last_err = None
    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            return call()
        except APIStatusError as e:
            last_err = e
            print(f"⚠️ API attempt {attempt}/{CLAUDE_MAX_RETRIES} failed — "
                  f"HTTP {e.status_code} | {type(e).__name__}: {e.message}"
                  f"{f' | request_id: {e.request_id}' if e.request_id else ''}")
        except Exception as e:
            last_err = e
            print(f"⚠️ API attempt {attempt}/{CLAUDE_MAX_RETRIES} failed — "
                  f"{type(e).__name__}: {e}")
    raise RuntimeError(f"Claude API failed after {CLAUDE_MAX_RETRIES} attempts: {last_err}") from last_err


def _call_cli(prompt):
    """Call Claude CLI with up to CLAUDE_MAX_RETRIES attempts; json_repair as fallback each time."""
    claude_bin = shutil.which('claude') or 'claude'
    env = {k: v for k, v in os.environ.items() if k not in ('CLAUDECODE', 'ANTHROPIC_API_KEY')}
    env['MAX_THINKING_TOKENS'] = '0'

    def call():
        result = subprocess.run(
            [claude_bin, '--model', CLAUDE_CLI_MODEL, '--print', prompt],
            capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise RuntimeError(
                f"Claude CLI failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        text = _strip_fences(result.stdout.strip())
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            text = repair_json(text, ensure_ascii=False)
            parsed = json.loads(text)  # raises if still invalid
            print("✅ JSON repaired")
        parsed = _normalize_digest(parsed)
        _validate_digest_structure(parsed)
        return json.dumps(parsed, ensure_ascii=False)

    last_err = None
    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            return call()
        except (RuntimeError, json.JSONDecodeError, ValueError) as e:
            last_err = e
            if attempt < CLAUDE_MAX_RETRIES:
                print(f"⚠️ Attempt {attempt} failed ({e}), retrying...")
    raise ValueError(f"Claude CLI failed after {CLAUDE_MAX_RETRIES} attempts: {last_err}")


def _build_prompt(all_articles):
    articles_by_category = []
    for category, articles in all_articles.items():
        if not articles:
            continue
        block = f"\n## {category}\n\n"
        for i, article in enumerate(articles[:15], 1):
            block += f"[{i}] {article['title']} | src: {article['source']}\n{article['summary']}\n\n"
        articles_by_category.append(block)

    full_content = "\n".join(articles_by_category)
    template = _PROMPT_PATH.read_text(encoding='utf-8')
    return template.replace('$articles', full_content).replace('$format_instructions', _FORMAT_INSTRUCTIONS)


def _strip_fences(text):
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    return text
