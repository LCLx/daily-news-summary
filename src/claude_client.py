import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from anthropic import Anthropic
from json_repair import repair_json

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_MAX_RETRIES

_PROMPT_PATH = Path(__file__).parent / 'prompts' / 'email_digest.md'

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
                        "category": {"type": "string"},
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "ref": {"type": "string"},
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
                    "required": ["category", "emoji", "items"],
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

    prompt = _build_prompt(all_articles)

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

    # Retry once on unexpected failure (network, etc.)
    try:
        return call()
    except RuntimeError:
        print("⚠️ API tool call failed, retrying...")
        return call()


def _call_cli(prompt):
    """Call Claude CLI with up to CLAUDE_MAX_RETRIES attempts; json_repair as fallback each time."""
    claude_bin = shutil.which('claude') or 'claude'
    env = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}

    def call():
        result = subprocess.run(
            [claude_bin, '--model', CLAUDE_MODEL, '--print', prompt],
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


def _build_prompt(all_articles):
    articles_by_category = []
    for category, articles in all_articles.items():
        if not articles:
            continue
        block = f"\n## {category}\n\n"
        for i, article in enumerate(articles[:15], 1):
            block += f"[{i}] {article['title']}\n"
            block += f"来源: {article['source']}\n"
            block += f"摘要: {article['summary']}\n"
            block += "\n"
        articles_by_category.append(block)

    full_content = "\n".join(articles_by_category)
    return _PROMPT_PATH.read_text(encoding='utf-8').replace('$articles', full_content)


def _strip_fences(text):
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    return text
