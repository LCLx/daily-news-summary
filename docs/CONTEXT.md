# Project Context

## What this is

Two parallel pipelines fetching from the same RSS sources:
- **Email pipeline** (`src/pipelines/email_pipeline.py`): RSS → Claude API → HTML email via Gmail. Runs on GitHub Actions daily at 08:00 PST (UTC 16:00).
- **Telegram pipeline** (`src/pipelines/telegram_pipeline.py`): RSS → Claude CLI (subscription, not API) → Telegram message.

## Stack

- Python 3.11, managed with **uv** (`uv sync`, `uv run`)
- `feedparser` — RSS parsing
- `anthropic` — Claude API; uses tool calling to guarantee valid JSON output
- `json-repair` — JSON repair fallback for CLI backend
- `python-dotenv` — loads `.env` for local dev (loaded in `core/config.py`)
- stdlib `json` + `html` — parse Claude's JSON output and render XSS-safe HTML (no `markdown` dependency)
- Gmail SMTP (`smtplib`) — email delivery (stdlib, no extra dependency)
- GitHub Actions — scheduling

## Project structure

```
src/
  core/                    # shared modules (imported as core.*)
    config.py              # RSS_SOURCES, env vars, CATEGORY_EMOJIS, CATEGORY_ZH_TO_RSS, CLAUDE_MAX_RETRIES
    rss.py                 # extract_image_url, fetch_rss_articles
    claude_client.py       # generate_summary_with_claude (API tool calling / CLI + json_repair)
    digest.py              # resolve_references (Claude JSON refs → full article data)
    renderer.py            # build_email_html_from_json (renders sections to HTML)
    mailer.py              # send_email_gmail
  pipelines/               # entry points
    email_pipeline.py      # main() — orchestrates the email pipeline
    telegram_pipeline.py   # telegram pipeline
  prompts/
    email_digest.md        # Claude prompt template ($articles placeholder)
  templates/
    email.html             # HTML email wrapper + CSS ($date_str, $body_html placeholders)
docs/
  CONTEXT.md               # this file
  REQUIREMENTS.md          # phase planning and requirements
tests/
  test_rss.py              # checks all feeds: reachability + recent article count
  test_claude.py           # full pipeline test, no email; writes generated/preview.html + preview.json
  test_email.py            # sends last generated preview via Gmail
  test_integration.py      # end-to-end: RSS → Claude → email; writes preview.html + preview.json
generated/                 # gitignored output directory
  preview.html             # local HTML preview matching exact email output
  preview.json             # raw Claude JSON output for debugging
pyproject.toml             # uv dependencies
.env                       # local secrets (gitignored)
.github/workflows/
  daily_news.yml           # CI: astral-sh/setup-uv + uv sync + uv run src/pipelines/email_pipeline.py
```

## Module responsibilities

| Module | Key functions |
|---|---|
| `core/config.py` | `RSS_SOURCES` dict, all env var constants, `CATEGORY_EMOJIS`, `CATEGORY_ZH_TO_RSS`, `CLAUDE_MAX_RETRIES` |
| `core/rss.py` | `extract_image_url(entry)` — tries media_content → media_thumbnail → HTML img parse; `fetch_rss_articles(category, feeds, hours=24)` — fetches RSS, filters to last 24h |
| `core/claude_client.py` | `generate_summary_with_claude(all_articles)` — loads prompt from `prompts/email_digest.md`; API path uses tool calling (guaranteed valid JSON); CLI path uses text output with `json_repair` fallback and up to `CLAUDE_MAX_RETRIES` attempts |
| `core/digest.py` | `resolve_references(parsed_json, all_articles)` — maps Claude's number-only refs (e.g. `"3"`) to full article dicts using section category context |
| `core/renderer.py` | `build_email_html_from_json(sections)` — renders section data into full HTML document using `templates/email.html` |
| `core/mailer.py` | `send_email_gmail(subject, body_html, recipients)` — Gmail SMTP with App Password |

## RSS sources

| Category | Sources |
|---|---|
| Tech & AI | The Verge, Wired, Techmeme (TechCrunch + Ars Technica commented out) |
| Global Affairs | The Guardian, BBC, NYT (NPR commented out) |
| Business & Finance | FT, Reuters (via Google News RSS), WSJ Markets |
| Pacific Northwest | Seattle Times, CBC British Columbia |
| Health & Science | ScienceDaily, Nature, NPR Health |
| Deals | Slickdeals, Reddit r/deals |

Note: Reuters official RSS is dead. Using Google News RSS proxy:
`https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com+business&ceid=US:en&hl=en-US&gl=US`

## Image extraction coverage

- `media_content`: Guardian
- `media_thumbnail`: BBC
- HTML `<img>` parse from `entry.content`: The Verge

## Env vars

```
# Email pipeline
ANTHROPIC_API_KEY=
GMAIL_USER=              # sender Gmail address
GMAIL_APP_PASSWORD=      # 16-char Gmail App Password
EMAIL_TO=                # comma-separated recipients

# Telegram pipeline
OPENCLAW_CONFIG=         # absolute path to openclaw.json
TELEGRAM_CHAT_ID=        # Telegram chat/channel ID

# Shared
CLAUDE_MODEL=            # required, API model ID, e.g. claude-haiku-4-5-20251001
CLAUDE_CLI_MODEL=        # optional, CLI model alias, e.g. haiku (defaults to haiku)
CLAUDE_BACKEND=cli       # optional; use Claude CLI subprocess instead of API

# Local dev / testing
MODE=TEST                # optional; limits test scripts to 1 article per category (faster, fewer tokens)
```

GitHub Actions (email pipeline): `ANTHROPIC_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `EMAIL_TO` as Secrets; `CLAUDE_MODEL` as Variable.

## Local dev workflow

```bash
uv sync                                      # install deps
uv run tests/test_rss.py                     # check feeds
uv run tests/test_claude.py                  # test Claude output + generate preview
open generated/preview.html                  # inspect email layout in browser
uv run tests/test_email.py                   # send preview via Gmail
uv run src/pipelines/email_pipeline.py       # full run including email
```

## Cost (approximate)

| Model | Per run | Per month (1×/day) |
|---|---|---|
| Haiku 4.5 | ~$0.014 | ~$0.42 |
| Sonnet 4.5 | ~$0.053 | ~$1.60 |

Current model: Haiku (user testing quality vs Sonnet).
