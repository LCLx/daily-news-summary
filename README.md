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
- **Email pipeline:** One summary backend (`BACKEND=BEDROCK_CLAUDE`, `CLAUDE_API`, `CLAUDE_CLI`, or `CODEX_CLI`) + Gmail account with an [App Password](https://myaccount.google.com/apppasswords). Gmail API OAuth2 support exists in code, but the current GitHub Actions setup uses SMTP/App Password.
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
# BACKEND=BEDROCK_CLAUDE   # or CLAUDE_API / CLAUDE_CLI / CODEX_CLI
# AWS_REGION=us-east-1
# MODEL=global.anthropic.claude-haiku-4-5-20251001-v1:0
# ANTHROPIC_API_KEY=...    # required only for BACKEND=CLAUDE_API
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
# BACKEND=CODEX_CLI MODEL=gpt-5.4-mini MODE=TEST uv run tests/test_llm.py

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
| `AWS_ROLE_ARN` | IAM role assumed by GitHub Actions via OIDC; required only for `BACKEND=BEDROCK_CLAUDE` |
| `ANTHROPIC_API_KEY` | Anthropic API key; required only for `BACKEND=CLAUDE_API` |
| `GMAIL_USER` | Gmail address used to send |
| `GMAIL_APP_PASSWORD` | 16-character Gmail App Password, current GitHub Actions email path |
| `EMAIL_TO` | Recipient address(es), comma-separated |

Gmail API OAuth2 secrets (`GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`) are optional and not needed for the current workflow.

GitHub Actions uses AWS OIDC to assume the role in `AWS_ROLE_ARN`; no static AWS access key secrets are required.

**Variables** (Settings → Secrets and variables → Actions → Variables):

Use the copy/paste blocks in `.env.example` for the Bedrock and Anthropic API configurations.

Current default model:

| Backend | Model | Cost/run | Quality |
|---|---|---|---|
| Bedrock Claude | `global.anthropic.claude-haiku-4-5-20251001-v1:0` | ~$0.01 | Good — fast, cheap |

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
| Bedrock Claude (Haiku, default for `BACKEND=BEDROCK_CLAUDE`) | ~$0.01/run · ~$0.30/month |
| Claude API (Haiku, default for `BACKEND=CLAUDE_API`) | ~$0.01/run · ~$0.30/month |
| Claude CLI / Codex CLI local testing | Uses your local subscription login, not the Anthropic API key |
| Gmail SMTP / Gmail API | Free |

## Stack

- Python 3.12+
- [feedparser](https://feedparser.readthedocs.io/) — RSS parsing
- [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) — AWS Bedrock runtime client
- [anthropic](https://github.com/anthropics/anthropic-sdk-python) — Claude API client
- [json-repair](https://github.com/mangiucugna/json_repair) — JSON repair fallback for API and CLI output
- Gmail SMTP (`smtplib`) with optional Gmail API support + stdlib `json`/`html` — email delivery and HTML rendering
- GitHub Actions — scheduling and execution

## License

MIT
