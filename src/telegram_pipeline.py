#!/usr/bin/env python3
"""
Daily news summary: RSS → Claude → Telegram
Run: uv run src/telegram_pipeline.py
"""
import re, json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')
from email_pipeline import fetch_rss_articles, RSS_SOURCES

OPENCLAW_CONFIG = os.environ['OPENCLAW_CONFIG']
CLAUDE_MODEL = os.environ['CLAUDE_MODEL']

PROMPT_TEMPLATE = """以下是今日各板块的英文新闻（已按板块分类）：

{articles}

请按以下要求生成中文新闻摘要，直接输出 Telegram HTML 格式（不要输出 markdown）：

每个板块选5条最重要的新闻，格式严格如下：

<b>💻 科技与AI</b>

<b>1. 中文标题</b>
100-150字中文摘要内容

🔗 <a href="原文链接">英文原标题</a>
📰 来源媒体名称

（每条新闻之间空一行，板块之间空两行）

板块顺序：科技与AI、国际时事、商业与金融、太平洋西北、健康与科学
"""

def fetch_articles():
    lines = []
    for category, feeds in RSS_SOURCES.items():
        articles = fetch_rss_articles(category, feeds)
        lines.append(f'\n## {category}\n')
        for i, a in enumerate(articles[:15], 1):
            lines.append(f'[{i}] {a["title"]}')
            lines.append(f'来源: {a.get("source", "")}')
            lines.append(f'时间: {a.get("published", "")}')
            lines.append(f'链接: {a["link"]}')
            lines.append(f'摘要: {a.get("summary", "")[:300]}')
            lines.append('')
    return '\n'.join(lines)

def generate_summary(articles_text):
    import subprocess
    claude_bin = shutil.which('claude') or 'claude'
    prompt = PROMPT_TEMPLATE.format(articles=articles_text)
    result = subprocess.run(
        [claude_bin, '--model', CLAUDE_MODEL,
         '--system-prompt', 'You are a helpful multilingual assistant. Output only the requested HTML content, no extra commentary.',
         '--print', prompt],
        capture_output=True, text=True, stdin=subprocess.DEVNULL
    )
    if result.returncode != 0 or not result.stdout.strip():
        print(f'Claude error (exit {result.returncode}): {result.stderr.strip()}', file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()

def fallback_strip_markdown(text):
    """If HTML tags missing, convert basic markdown to HTML as fallback."""
    text = re.sub(r'^## (.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    text = re.sub(r'🔗\s*(https?://\S+)\s*\n📰\s*(.+)', r'📰 <a href="\1">\2</a>', text)
    text = re.sub(r'🔗\s*https?://\S+\n?', '', text)
    text = re.sub(r'\n---+\n?', '\n', text)
    return text.strip()

def send_to_telegram(text, bot_token, chat_id):
    # Split only on category headers (lines starting with <b> followed by emoji)
    sections = [s.strip() for s in re.split(r'\n{2,}(?=<b>[^\d<])', text) if s.strip()]
    if not sections:
        sections = [text]  # fallback: send as one chunk

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    for s in sections:
        if len(s) > 4000:
            # Emergency split
            s = s[:4000] + '...'
        data = json.dumps({
            'chat_id': chat_id,
            'text': s,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }).encode()
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        try:
            res = json.loads(urllib.request.urlopen(req).read())
        except urllib.error.URLError as e:
            print(f'Network error: {e}', file=sys.stderr)
            continue
        if not res.get('ok'):
            print(f'Send error: {res}', file=sys.stderr)

def main():
    cfg = json.loads(open(OPENCLAW_CONFIG).read())
    bot_token = cfg['channels']['telegram']['botToken']
    chat_id = os.environ['TELEGRAM_CHAT_ID']

    print('Fetching RSS...')
    articles = fetch_articles()

    print('Generating summary...')
    summary = generate_summary(articles)

    # Detect if output looks like HTML or markdown (fallback)
    if '<b>' not in summary and '##' in summary:
        print('Warning: HTML not detected, applying fallback conversion')
        summary = fallback_strip_markdown(summary)

    print('Sending to Telegram...')
    send_to_telegram(summary, bot_token, chat_id)
    print('Done.')

if __name__ == '__main__':
    main()
