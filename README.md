# daily-news-summary

Two parallel pipelines that fetch RSS feeds and deliver Chinese summaries via different channels:

- **Email pipeline** — RSS + gas prices + market data → configured LLM backend → HTML email via Gmail SMTP/App Password. Runs daily on GitHub Actions.
- **Telegram pipeline** — Claude CLI (subscription) → Telegram message. Run manually or on schedule.

Both pipelines fetch articles published in the last 24 hours, select the most newsworthy items, and write concise Chinese summaries. The email pipeline also appends Vancouver/Seattle gas prices and an optional US market pulse section.

## Categories and sources

| Category | Sources |
|---|---|
| Tech & AI | The Verge, Wired, Techmeme |
| Global Affairs | The Guardian, BBC, NYT |
| Business & Finance | Financial Times, Reuters (via Google News), WSJ Markets |
| Pacific Northwest | Seattle Times, CBC British Columbia |
| Health & Science | ScienceDaily, Nature, NPR Health |

The email pipeline also fetches a separate stock-market RSS set for the market pulse narrative. Those articles are not rendered as normal news items.

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/)
- **Email pipeline:** One summary backend (`BACKEND=CLAUDE_API`, `CLAUDE_CLI`, or `CODEX_CLI`) + Gmail account with an [App Password](https://myaccount.google.com/apppasswords). Gmail API OAuth2 support exists in code, but the current GitHub Actions setup uses SMTP/App Password.
- **Telegram pipeline:** [Claude CLI](https://claude.ai/code) logged in with a Claude subscription + a Telegram bot token

### Local development

```bash
git clone <your-repo-url>
cd daily-news-summary

# Install dependencies
uv sync

# Configure environment:
# cp .env.example .env
# Email pipeline:
# BACKEND=CLAUDE_API        # or CLAUDE_CLI / CODEX_CLI for local subscription-backed testing
# MODEL=claude-haiku-4-5-20251001
# ANTHROPIC_API_KEY=...
# GMAIL_USER=your.address@gmail.com
# Current GitHub Actions path:
# GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   (16-char App Password)
# EMAIL_TO=recipient@example.com
# Optional Gmail API mode, not currently configured in GitHub Actions:
# GMAIL_CLIENT_ID=...
# GMAIL_CLIENT_SECRET=...
# GMAIL_REFRESH_TOKEN=...
#
# Telegram pipeline:
# OPENCLAW_CONFIG=/path/to/.openclaw/openclaw.json
# TELEGRAM_CHAT_ID=your_chat_id
#
# Shared:
# MODE=TEST

# Run email pipeline
uv run src/pipelines/email_pipeline.py

# Local subscription-backed testing examples:
# BACKEND=CLAUDE_CLI MODEL=haiku MODE=TEST uv run tests/test_llm.py
# BACKEND=CODEX_CLI MODE=TEST uv run tests/test_llm.py

# Run Telegram pipeline
uv run src/pipelines/telegram_pipeline.py
```

### Testing

```bash
# Unit tests
uv run pytest

# Test RSS feed availability
uv run tests/test_rss.py

# Test configured LLM output with real RSS data, saves generated/preview.html (no email sent)
uv run tests/test_llm.py

# Test Gmail email delivery using the last generated preview
uv run tests/test_email.py

# Full end-to-end integration test (RSS → LLM → email)
uv run tests/test_integration.py
```

### GitHub Actions

Add the following secrets to your repository under **Settings → Secrets and variables → Actions → Secrets**:

| Secret | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GMAIL_USER` | Gmail address used to send |
| `GMAIL_APP_PASSWORD` | 16-character Gmail App Password, current GitHub Actions email path |
| `EMAIL_TO` | Recipient address(es), comma-separated |

Gmail API OAuth2 secrets (`GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`) are optional and not needed for the current workflow.

**Variables** (Settings → Secrets and variables → Actions → Variables):

| Variable | Description |
|---|---|
| `BACKEND` | Summary backend: `CLAUDE_API`, `CLAUDE_CLI`, or `CODEX_CLI`. The GitHub Actions workflow sets `CLAUDE_API` directly. |
| `MODEL` | Optional backend model/alias. Defaults: Claude API uses `claude-haiku-4-5-20251001`, Claude CLI uses `haiku`, Codex CLI uses its own configured default |

Available models:

| Model | Cost/run | Quality |
|---|---|---|
| `claude-haiku-4-5-20251001` | ~$0.01 | Good — fast, cheap |
| `claude-sonnet-4-5-20250929` | ~$0.10 | Better — recommended for quality |
| `claude-opus-4-6` | ~$0.50 | Best — highest quality |

The workflow runs automatically on schedule and can also be triggered manually via `workflow_dispatch`.

## Configuration

| What to change | Where |
|---|---|
| RSS feeds | `src/core/config.py` — `RSS_SOURCES` dict |
| Stock market feeds / indices | `src/core/config.py` — `STOCK_RSS_FEEDS` and `STOCK_INDICES` |
| Digest prompt / selection rules | `src/prompts/email_digest.md` |
| Email layout and CSS | `src/templates/email.html` |
| Lookback window (default 24h) | `hours` parameter in `fetch_rss_articles()` in `src/core/rss.py` |

## Cost

| Service | Cost |
|---|---|
| Claude API (Haiku, default for `BACKEND=CLAUDE_API`) | ~$0.01/run · ~$0.30/month |
| Claude CLI / Codex CLI local testing | Uses your local subscription login, not the Anthropic API key |
| Gmail SMTP / Gmail API | Free |

## Stack

- Python 3.12+
- [feedparser](https://feedparser.readthedocs.io/) — RSS parsing
- [anthropic](https://github.com/anthropics/anthropic-sdk-python) — Claude API client
- [json-repair](https://github.com/mangiucugna/json_repair) — JSON repair fallback for API and CLI output
- Gmail SMTP (`smtplib`) with optional Gmail API support + stdlib `json`/`html` — email delivery and HTML rendering
- GitHub Actions — scheduling and execution

## License

MIT
