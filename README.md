# daily-news-summary

Two parallel pipelines that fetch from the same RSS feeds and deliver Chinese summaries via different channels:

- **Email pipeline** — Claude API → HTML email via Gmail SMTP. Runs daily on GitHub Actions at 08:00 PST (UTC 16:00).
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
- **Email pipeline:** An [Anthropic API key](https://console.anthropic.com/) + Gmail account with [App Password](https://myaccount.google.com/apppasswords) enabled
- **Telegram pipeline:** [Claude CLI](https://claude.ai/code) logged in with a Claude subscription + a Telegram bot token

### Local development

```bash
git clone <your-repo-url>
cd daily-news-summary

# Install dependencies
uv sync

# Configure environment — create a .env file:
# Email pipeline:
# ANTHROPIC_API_KEY=...
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

### GitHub Actions

Add the following secrets to your repository under **Settings → Secrets and variables → Actions → Secrets**:

| Secret | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GMAIL_USER` | Gmail address used to send |
| `GMAIL_APP_PASSWORD` | 16-character Gmail App Password |
| `EMAIL_TO` | Recipient address(es), comma-separated |

**Variables** (Settings → Secrets and variables → Actions → Variables):

| Variable | Description |
|---|---|
| `CLAUDE_MODEL` | Claude model ID (see options below, default: `claude-haiku-4-5-20251001`) |

Available models:

| Model | Cost/run | Quality |
|---|---|---|
| `claude-haiku-4-5-20251001` | ~$0.01 | Good — fast, cheap |
| `claude-sonnet-4-5-20250929` | ~$0.10 | Better — recommended for quality |
| `claude-opus-4-6` | ~$0.50 | Best — highest quality |

The workflow runs automatically on schedule and can also be triggered manually via `workflow_dispatch`.

## Configuration

All configuration lives in `email_pipeline.py`:

- **`RSS_SOURCES`** — add or remove feeds per category; the dict key becomes the section heading passed to Claude
- **`hours` parameter** in `fetch_rss_articles()` — controls the lookback window (default: 24h)
- **Prompt** in `generate_summary_with_claude()` — controls output format and article count per section

## Cost

| Service | Cost |
|---|---|
| Claude (Haiku, default) | ~$0.01/run · ~$0.30/month |
| Gmail SMTP | Free |

## Stack

- Python 3.11
- [feedparser](https://feedparser.readthedocs.io/) — RSS parsing
- [anthropic](https://github.com/anthropics/anthropic-sdk-python) — Claude API client
- Gmail SMTP (`smtplib`) + stdlib `json`/`html` — email delivery and HTML rendering (no extra dependencies)
- GitHub Actions — scheduling and execution

## License

MIT
