# daily-news-summary

Automated daily news digest that fetches articles from RSS feeds, summarizes them in Chinese using the Claude API, and delivers the result via email.

Runs daily on GitHub Actions at 08:00 PST / 09:00 PDT (UTC 16:00).

## How it works

1. Fetches articles published in the last 24 hours from RSS feeds across four categories
2. Passes the raw articles to Claude, which selects the most newsworthy items and writes concise Chinese summaries
3. Renders the markdown output as HTML and sends it via Resend

## Categories and sources

| Category | Sources |
|---|---|
| 国际政治 | The Guardian, BBC, NPR |
| 经济与商业 | Financial Times, Reuters (via Google News), WSJ Markets |
| 科技与AI | TechCrunch, The Verge, Ars Technica, Wired |
| 健康与科学 | ScienceDaily, Nature, NPR Health |

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/)
- An [Anthropic API key](https://console.anthropic.com/)
- A [Resend API key](https://resend.com/api-keys)

### Local development

```bash
git clone <your-repo-url>
cd daily-news-summary

# Install dependencies
uv sync

# Configure environment
cp .env .env.local  # or create .env manually
# Set ANTHROPIC_API_KEY, RESEND_API_KEY, EMAIL_TO

# Run
uv run daily_news.py
```

### Testing

```bash
# Test RSS feed availability
uv run test_rss.py

# Test Claude output with real RSS data (no email sent)
uv run test_claude.py
```

### GitHub Actions

Add the following secrets to your repository under **Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `RESEND_API_KEY` | Resend API key |
| `EMAIL_TO` | Recipient address(es), comma-separated |

The workflow runs automatically on schedule and can also be triggered manually via `workflow_dispatch`.

## Configuration

All configuration lives in `daily_news.py`:

- **`RSS_SOURCES`** — add or remove feeds per category; the dict key becomes the section heading passed to Claude
- **`hours` parameter** in `fetch_rss_articles()` — controls the lookback window (default: 24h)
- **Prompt** in `generate_summary_with_claude()` — controls output format and article count per section
- **`EMAIL_FROM`** — update to a verified custom domain if you have one configured in Resend

## Cost

| Service | Cost |
|---|---|
| Claude API (Sonnet 4.5) | ~$0.05/run · ~$1.5/month |
| Resend | Free up to 3,000 emails/month |

## Stack

- Python 3.11
- [feedparser](https://feedparser.readthedocs.io/) — RSS parsing
- [anthropic](https://github.com/anthropics/anthropic-sdk-python) — Claude API client
- [markdown](https://python-markdown.github.io/) — markdown to HTML rendering
- [resend](https://resend.com/docs/send-with-python) — email delivery
- GitHub Actions — scheduling and execution

## License

MIT
