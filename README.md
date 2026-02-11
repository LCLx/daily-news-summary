# daily-news-summary

Automated daily news digest that fetches articles from RSS feeds, summarizes them in Chinese using the Claude API, and delivers the result via Gmail.

Runs daily on GitHub Actions at 08:00 PST / 09:00 PDT (UTC 16:00).

## How it works

1. Fetches articles published in the last 24 hours from RSS feeds across four categories
2. Passes the raw articles to Claude, which selects the most newsworthy items and writes concise Chinese summaries
3. Renders the markdown output as HTML and sends it via Gmail SMTP

## Categories and sources

| Category | Sources |
|---|---|
| World Politics | The Guardian, BBC, NPR |
| Economy & Business | Financial Times, Reuters (via Google News), WSJ Markets |
| Tech & AI | TechCrunch, The Verge, Ars Technica, Wired, Techmeme |
| Health & Science | ScienceDaily, Nature, NPR Health |

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/)
- An [Anthropic API key](https://console.anthropic.com/)
- A Gmail account with [App Password](https://myaccount.google.com/apppasswords) enabled (requires 2-Step Verification)

### Local development

```bash
git clone <your-repo-url>
cd daily-news-summary

# Install dependencies
uv sync

# Configure environment — create a .env file with:
# ANTHROPIC_API_KEY=...
# GMAIL_USER=your.address@gmail.com
# GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   (16-char App Password)
# EMAIL_TO=recipient@example.com

# Run
uv run src/daily_news.py
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

All configuration lives in `daily_news.py`:

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
- [markdown](https://python-markdown.github.io/) — markdown to HTML rendering
- Gmail SMTP (`smtplib`) — email delivery (stdlib, no extra dependency)
- GitHub Actions — scheduling and execution

## License

MIT
