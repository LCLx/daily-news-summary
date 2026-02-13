# daily-news-summary

Two parallel pipelines that fetch from the same RSS feeds and deliver Chinese summaries via different channels:

- **Email pipeline** — Claude CLI → HTML email via Gmail SMTP. Runs via local cron job.
- **Telegram pipeline** — Claude CLI (subscription) → Telegram message. Run manually or on schedule.

Both pipelines fetch articles published in the last 24 hours, select the most newsworthy items, and write concise Chinese summaries.

## Categories and sources

| Category | Sources |
|---|---|
| Tech & AI | The Verge, Wired, Techmeme |
| Global Affairs | The Guardian, BBC, NYT |
| Business & Finance | Financial Times, Reuters (via Google News), WSJ Markets |
| Pacific Northwest | Seattle Times, CBC British Columbia |
| Health & Science | ScienceDaily, Nature, NPR Health |

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/)
- [Claude CLI](https://claude.ai/code) logged in with a Claude subscription
- **Email pipeline:** Gmail account with [App Password](https://myaccount.google.com/apppasswords) enabled
- **Telegram pipeline:** A Telegram bot token

### Local development

```bash
git clone <your-repo-url>
cd daily-news-summary

# Install dependencies
uv sync

# Configure environment — create a .env file:
# Email pipeline:
# GMAIL_USER=your.address@gmail.com
# GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   (16-char App Password)
# EMAIL_TO=recipient@example.com
#
# Telegram pipeline:
# OPENCLAW_CONFIG=/path/to/.openclaw/openclaw.json
# TELEGRAM_CHAT_ID=your_chat_id
#
# Shared:
# CLAUDE_MODEL=claude-haiku-4-5-20251001

# Run email pipeline
uv run src/email_pipeline.py

# Run Telegram pipeline
uv run src/telegram_pipeline.py
```

### Testing

```bash
# Test RSS feed availability
uv run tests/test_rss.py

# Test Claude output with real RSS data, saves generated/preview.html (no email sent)
uv run tests/test_claude.py

# Test Gmail email delivery using the last generated preview
uv run tests/test_email.py

# Full end-to-end integration test (RSS → Claude → email)
uv run tests/test_integration.py
```

## Configuration

All configuration lives in `email_pipeline.py`:

- **`RSS_SOURCES`** — add or remove feeds per category; the dict key becomes the section heading passed to Claude
- **`hours` parameter** in `fetch_rss_articles()` — controls the lookback window (default: 24h)
- **Prompt** in `generate_summary_with_claude()` — controls output format and article count per section

## Stack

- Python 3.11
- [feedparser](https://feedparser.readthedocs.io/) — RSS parsing
- Claude CLI (subscription) — LLM summarization
- [markdown](https://python-markdown.github.io/) — markdown to HTML rendering
- Gmail SMTP (`smtplib`) — email delivery (stdlib, no extra dependency)

## License

MIT
