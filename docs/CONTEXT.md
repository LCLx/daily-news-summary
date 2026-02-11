# Project Context

## What this is

Daily news digest: fetches RSS → Claude summarizes in Chinese → Gmail delivers HTML email.
Runs on GitHub Actions daily at 08:00 PST (UTC 16:00).

## Stack

- Python 3.11, managed with **uv** (`uv sync`, `uv run`)
- `feedparser` — RSS parsing
- `anthropic` — Claude API (currently `claude-haiku-4-5-20251001`)
- `markdown` — markdown → HTML
- `python-dotenv` — loads `.env` for local dev
- Gmail SMTP (`smtplib`) — email delivery (stdlib, no extra dependency)
- GitHub Actions — scheduling

## Project structure

```
src/
  daily_news.py            # main script (all logic lives here)
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
.github/workflows/
  daily_news.yml           # CI: astral-sh/setup-uv + uv sync + uv run src/daily_news.py
```

## Key functions in src/daily_news.py

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
| World Politics | The Guardian, BBC, NPR |
| Economy & Business | FT, Reuters (via Google News RSS), WSJ Markets |
| Tech & AI | TechCrunch, The Verge, Ars Technica, Wired, Techmeme |
| Health & Science | ScienceDaily, Nature, NPR Health |

Note: Reuters official RSS is dead. Using Google News RSS proxy:
`https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com+business&ceid=US:en&hl=en-US&gl=US`

## Image extraction coverage

- `media_thumbnail`: BBC, Ars Technica
- `media_content`: Guardian, Ars Technica
- HTML `<img>` parse from `entry.content`: The Verge
- TechCrunch: no images (text-only feed)

## Env vars

```
ANTHROPIC_API_KEY=
GMAIL_USER=              # sender Gmail address
GMAIL_APP_PASSWORD=      # 16-char Gmail App Password
EMAIL_TO=                # comma-separated recipients
CLAUDE_MODEL=            # optional, defaults to claude-haiku-4-5-20251001
```

GitHub Actions: `ANTHROPIC_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `EMAIL_TO` as Secrets;
`CLAUDE_MODEL` as Variable.

## Local dev workflow

```bash
uv sync                              # install deps
uv run tests/test_rss.py             # check feeds
uv run tests/test_claude.py          # test Claude output + generate preview
open generated/preview.html          # inspect email layout in browser
uv run tests/test_email.py           # send preview via Gmail
uv run src/daily_news.py             # full run including email
```

## Cost (approximate)

| Model | Per run | Per month (1×/day) |
|---|---|---|
| Haiku 4.5 | ~$0.014 | ~$0.42 |
| Sonnet 4.5 | ~$0.053 | ~$1.60 |

Current model: Haiku (user testing quality vs Sonnet).
