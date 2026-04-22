# daily-news-summary

Two parallel pipelines that fetch from the same RSS feeds and deliver Chinese summaries via different channels:

- **Email pipeline** — Claude CLI → HTML email via Gmail API (OAuth2).
- **Telegram pipeline** — Claude CLI → Telegram message.

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
- Gmail account with OAuth2 credentials (Client ID, Client Secret, Refresh Token)
- **Telegram pipeline:** a Telegram bot token

### Local development

```bash
git clone <your-repo-url>
cd daily-news-summary

# Install dependencies
uv sync

# Configure environment — create a .env file:
# Email pipeline:
# GMAIL_USER=your.address@gmail.com
# GMAIL_CLIENT_ID=...
# GMAIL_CLIENT_SECRET=...
# GMAIL_REFRESH_TOKEN=...
# EMAIL_TO=recipient@example.com
#
# Telegram pipeline:
# TELEGRAM_BOT_TOKEN=your_bot_token
# TELEGRAM_CHAT_ID=your_chat_id
#
# Shared:
# CLAUDE_CLI_MODEL=haiku

# One-time: generate GMAIL_REFRESH_TOKEN
# (requires http://localhost as an Authorized redirect URI on the OAuth client)
uv run scripts/get_refresh_token.py

# Run email pipeline
uv run src/pipelines/email_pipeline.py

# Run Telegram pipeline
uv run src/pipelines/telegram_pipeline.py
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

| What to change | Where |
|---|---|
| RSS feeds | `src/core/config.py` — `RSS_SOURCES` dict |
| Claude prompt / selection rules | `src/prompts/email_digest.md` |
| Email layout and CSS | `src/templates/email.html` |
| Lookback window (default 24h) | `hours` parameter in `fetch_rss_articles()` in `src/core/rss.py` |

## Stack

- Python 3.12
- [feedparser](https://feedparser.readthedocs.io/) — RSS parsing
- [Claude CLI](https://claude.ai/code) — digest generation via `claude -p`
- [json-repair](https://github.com/mangiucugna/json_repair) — JSON repair fallback
- Gmail API (OAuth2) — email delivery
- stdlib `json`/`html` — JSON parsing and XSS-safe HTML rendering

## License

MIT
