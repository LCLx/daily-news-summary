# Project Context

## What this is

Two parallel pipelines fetching from the same RSS sources:
- **Email pipeline** (`src/email_pipeline.py`): RSS → Claude CLI → HTML email via Gmail. Runs via local cron job.
- **Telegram pipeline** (`src/telegram_pipeline.py`): RSS → Claude CLI → Telegram message.

## Stack

- Python 3.11, managed with **uv** (`uv sync`, `uv run`)
- `feedparser` — RSS parsing
- Claude CLI (subscription) — LLM summarization for both pipelines
- `markdown` — markdown → HTML
- `python-dotenv` — loads `.env` for local dev
- Gmail SMTP (`smtplib`) — email delivery (stdlib, no extra dependency)

## Project structure

```
src/
  email_pipeline.py        # email pipeline (all logic lives here)
  telegram_pipeline.py     # telegram pipeline (calls Claude CLI via subprocess)
docs/
  CONTEXT.md               # this file
  REQUIREMENTS.md          # phase planning and requirements
tests/
  test_rss.py              # checks all feeds: reachability + recent article count
  test_claude.py           # full pipeline test, no email; writes generated/preview.html
  test_email.py            # sends last generated preview via Gmail
  test_integration.py      # end-to-end: RSS → Claude → email
generated/                 # gitignored output directory
  preview.html             # local HTML preview matching exact email output
pyproject.toml             # uv dependencies
.env                       # local secrets (gitignored)
```

## Key functions in src/email_pipeline.py

| Function | What it does |
|---|---|
| `extract_image_url(entry)` | Tries media_thumbnail → media_content → HTML img parse; returns None if none found |
| `fetch_rss_articles(category, feeds, hours=24)` | Fetches RSS, filters to last 24h (UTC), stores image_url per article |
| `generate_summary_with_claude(all_articles)` | Builds prompt, calls Claude, returns markdown |
| `build_email_html(body_markdown)` | Renders markdown to full HTML email via `markdown` lib |
| `send_email_gmail(subject, body_markdown, recipients)` | Sends via Gmail SMTP with App Password |
| `main()` | Orchestrates fetch → summarize → print → email |

## RSS sources

| Category | Sources |
|---|---|
| Tech & AI | The Verge, Wired, Techmeme (TechCrunch + Ars Technica commented out) |
| Global Affairs | The Guardian, BBC, NYT (NPR commented out) |
| Business & Finance | FT, Reuters (via Google News RSS), WSJ Markets |
| Pacific Northwest | Seattle Times, CBC British Columbia |
| Health & Science | ScienceDaily, Nature, NPR Health |

Note: Reuters official RSS is dead. Using Google News RSS proxy:
`https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com+business&ceid=US:en&hl=en-US&gl=US`

## Image extraction coverage

- `media_thumbnail`: BBC
- `media_content`: Guardian
- HTML `<img>` parse from `entry.content`: The Verge

## Env vars

```
# Email pipeline
GMAIL_USER=              # sender Gmail address
GMAIL_APP_PASSWORD=      # 16-char Gmail App Password
EMAIL_TO=                # comma-separated recipients

# Telegram pipeline
OPENCLAW_CONFIG=         # absolute path to openclaw.json
TELEGRAM_CHAT_ID=        # Telegram chat/channel ID

# Shared (both pipelines)
CLAUDE_MODEL=            # required, e.g. claude-haiku-4-5-20251001
```

## Local dev workflow

```bash
uv sync                              # install deps
uv run tests/test_rss.py             # check feeds
uv run tests/test_claude.py          # test Claude output + generate preview
open generated/preview.html          # inspect email layout in browser
uv run tests/test_email.py           # send preview via Gmail
uv run src/email_pipeline.py             # full run including email
```

