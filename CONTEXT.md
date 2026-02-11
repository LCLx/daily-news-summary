# Project Context

## What this is

Daily news digest: fetches RSS → Claude summarizes in Chinese → Resend delivers HTML email.
Runs on GitHub Actions daily at 08:00 PST (UTC 16:00).

## Stack

- Python 3.11, managed with **uv** (`uv sync`, `uv run`)
- `feedparser` — RSS parsing
- `anthropic` — Claude API (currently `claude-haiku-4-5-20251001`, was sonnet)
- `markdown` — markdown → HTML (replaces hand-rolled converter)
- `python-dotenv` — loads `.env` for local dev
- `resend` — email delivery
- GitHub Actions — scheduling

## Project structure

```
daily_news.py            # main script (all logic lives here)
pyproject.toml           # uv dependencies
.env                     # local secrets (gitignored)
tests/
  test_rss.py            # checks all feeds: reachability + recent article count
  test_claude.py         # full pipeline test, no email; writes generated/preview.html
generated/               # gitignored output directory
  preview.html           # local HTML preview matching exact email output
.github/workflows/
  daily_news.yml         # CI: astral-sh/setup-uv + uv sync + uv run daily_news.py
```

## Key functions in daily_news.py

| Function | What it does |
|---|---|
| `extract_image_url(entry)` | Tries media_thumbnail → media_content → HTML img parse; returns None if none found |
| `fetch_rss_articles(category, feeds, hours=24)` | Fetches RSS, filters to last 24h (UTC), stores image_url per article |
| `generate_summary_with_claude(all_articles)` | Builds prompt, calls Claude, returns markdown |
| `build_email_html(body_markdown)` | Renders markdown to full HTML email via `markdown` lib |
| `send_email_resend(subject, body_markdown, recipients)` | Sends via Resend |
| `main()` | Orchestrates fetch → summarize → print → email |

## RSS sources

| Category | Sources |
|---|---|
| 国际政治 | The Guardian, BBC, NPR |
| 经济与商业 | FT, Reuters via Google News RSS, WSJ Markets |
| 科技与AI | TechCrunch, The Verge, Ars Technica, Wired |
| 健康与科学 | ScienceDaily, Nature, NPR Health |

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
RESEND_API_KEY=
EMAIL_TO=          # comma-separated recipients
```

GitHub Actions secrets: same three keys under Settings → Secrets → Actions.

## Local dev workflow

```bash
uv sync                          # install deps
uv run tests/test_rss.py         # check feeds
uv run tests/test_claude.py      # test Claude output + generate preview
open generated/preview.html      # inspect email layout in browser
uv run daily_news.py             # full run including email
```

## Cost (approximate)

| Model | Per run | Per month (1×/day) |
|---|---|---|
| Haiku 4.5 | ~$0.014 | ~$0.42 |
| Sonnet 4.5 | ~$0.053 | ~$1.60 |

Current model: Haiku (user testing quality vs Sonnet).
