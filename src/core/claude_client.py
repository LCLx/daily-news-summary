import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from anthropic import Anthropic
from json_repair import repair_json

from core.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_CLI_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_MAX_RETRIES

_PROMPT_PATH = Path(__file__).parent.parent / 'prompts' / 'email_digest.md'

# CLI-only: JSON format instructions (API mode uses tool schema instead, saving input tokens)
_CLI_FORMAT_INSTRUCTIONS = """输出一个 JSON 对象，不要任何其他内容（无 markdown、无开场白、无结束语）。

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

# Tool schema for structured JSON output via API tool calling.
# Forces Claude to return valid JSON matching this schema — eliminates parse errors.
_DIGEST_TOOL = {
    "name": "create_digest",
    "input_schema": {
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["科技与AI", "国际政治", "经济与商业", "太平洋西北地区", "健康与科学", "今日优惠"],
                        },
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "ref": {"type": "string", "description": "Article number from the input, e.g. \"3\""},
                                    "title_zh": {"type": "string"},
                                    "summary_zh": {"type": "string"},
                                    "price": {"type": "string"},
                                    "original_price": {"type": "string"},
                                    "discount": {"type": "string"},
                                    "store": {"type": "string"},
                                },
                                "required": ["ref", "title_zh", "summary_zh"],
                            }
                        },
                    },
                    "required": ["category", "items"],
                }
            }
        },
        "required": ["sections"],
    },
}


def generate_summary_with_claude(all_articles):
    """
    Generate a Chinese digest via Claude API or CLI.

    Backend selection (checked in order):
      1. CLAUDE_BACKEND=cli  → Claude CLI subprocess (local dev / subscription)
      2. ANTHROPIC_API_KEY set → Anthropic API tool calling (GitHub Actions / CI)
      3. Neither set          → raises ValueError

    Args:
        all_articles: dict of articles grouped by category name

    Returns:
        str: JSON string with "sections" key
    """
    use_cli = os.environ.get('CLAUDE_BACKEND', '').lower() == 'cli'
    if not use_cli and not ANTHROPIC_API_KEY:
        raise ValueError("Set ANTHROPIC_API_KEY (API) or CLAUDE_BACKEND=cli (CLI)")

    prompt = _build_prompt(all_articles, use_api=not use_cli)

    if use_cli:
        print("Calling Claude CLI to generate digest...")
        return _call_cli(prompt)
    else:
        print("Calling Claude API to generate digest...")
        return _call_api(prompt)


def _call_api(prompt):
    """Use Anthropic tool calling to guarantee valid JSON output."""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    def call():
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            tools=[_DIGEST_TOOL],
            tool_choice={"type": "tool", "name": "create_digest"},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in message.content:
            if block.type == "tool_use":
                return json.dumps(block.input, ensure_ascii=False)
        raise RuntimeError("Claude API did not call the expected tool")

    last_err = None
    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            return call()
        except Exception as e:
            last_err = e
            if attempt < CLAUDE_MAX_RETRIES:
                print(f"⚠️ API attempt {attempt} failed ({e}), retrying...")
    raise RuntimeError(f"Claude API failed after {CLAUDE_MAX_RETRIES} attempts: {last_err}") from last_err


def _call_cli(prompt):
    """Call Claude CLI with up to CLAUDE_MAX_RETRIES attempts; json_repair as fallback each time."""
    claude_bin = shutil.which('claude') or 'claude'
    env = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
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
            json.loads(text)
            return text
        except json.JSONDecodeError:
            repaired = repair_json(text, ensure_ascii=False)
            json.loads(repaired)  # raises if still invalid
            print("✅ JSON repaired")
            return repaired

    last_err = None
    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            return call()
        except (RuntimeError, json.JSONDecodeError, ValueError) as e:
            last_err = e
            if attempt < CLAUDE_MAX_RETRIES:
                print(f"⚠️ Attempt {attempt} failed ({e}), retrying...")
    raise ValueError(f"Claude CLI failed after {CLAUDE_MAX_RETRIES} attempts: {last_err}")


def _build_prompt(all_articles, *, use_api=False):
    articles_by_category = []
    for category, articles in all_articles.items():
        if not articles:
            continue
        block = f"\n## {category}\n\n"
        for i, article in enumerate(articles[:15], 1):
            block += f"[{i}] {article['title']} | src: {article['source']}\n{article['summary']}\n\n"
        articles_by_category.append(block)

    full_content = "\n".join(articles_by_category)
    format_instructions = '' if use_api else _CLI_FORMAT_INSTRUCTIONS
    template = _PROMPT_PATH.read_text(encoding='utf-8')
    return template.replace('$articles', full_content).replace('$format_instructions', format_instructions)


def _strip_fences(text):
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    return text
