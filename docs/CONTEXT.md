# Project Context

## What this is

Two parallel pipelines fetching from the shared RSS sources:
- **Email pipeline** (`src/pipelines/email_pipeline.py`): RSS + gas prices + US market data → configured LLM backend → HTML email via Gmail SMTP/App Password. Runs on GitHub Actions daily.
- **Telegram pipeline** (`src/pipelines/telegram_pipeline.py`): RSS → Claude CLI (subscription, not API) → Telegram message.

## Stack

- Python 3.12+, managed with **uv** (`uv sync`, `uv run`)
- `feedparser` — RSS parsing
- `anthropic` — Claude API client
- `boto3` — AWS Bedrock runtime client for Claude on GitHub Actions
- `json-repair` — JSON repair fallback for API and CLI JSON output
- `python-dotenv` — loads `.env` for local dev (loaded in `core/config.py`)
- stdlib `json` + `html` — parse LLM JSON output and render XSS-safe HTML (no `markdown` dependency)
- Gmail SMTP (`smtplib`) with App Password is the current deployment path; Gmail API support exists but is not configured in GitHub Actions.
- GitHub Actions — scheduling

## Project structure

```
src/
  core/                    # shared modules (imported as core.*)
    config.py              # RSS_SOURCES, STOCK_RSS_FEEDS, STOCK_INDICES, env vars, category maps
    rss.py                 # extract_image_url, fetch_rss_articles
    llm_client.py          # generate_summary (Bedrock Claude, Claude API, Claude CLI, or Codex CLI text output + json_repair)
    digest.py              # resolve_references / resolve_market_pulse
    renderer.py            # build_email_html_from_json (news, market pulse, gas cards)
    gas_prices.py          # Vancouver + Seattle gas prices
    stock_market.py        # CNBC index snapshot fetcher for market pulse
    mailer.py              # send_email_gmail (Gmail SMTP/App Password path used in GA; Gmail API support retained)
  pipelines/               # entry points
    email_pipeline.py      # main() — orchestrates the email pipeline
    telegram_pipeline.py   # telegram pipeline
  prompts/
    email_digest.md        # digest prompt template ($articles, $stock_block placeholders)
  templates/
    email.html             # HTML email wrapper + CSS ($date_str, $body_html placeholders)
docs/
  CONTEXT.md               # this file
  REQUIREMENTS.md          # phase planning and requirements
tests/
  test_rss.py              # checks all feeds: reachability + recent article count
  test_llm.py              # full pipeline test, no email; writes generated/preview.html + preview.json
  test_email.py            # sends last generated preview via Gmail
  test_integration.py      # end-to-end: RSS → LLM → email; writes preview.html + preview.json
generated/                 # gitignored output directory
  preview.html             # local HTML preview matching exact email output
  preview.json             # raw LLM JSON output for debugging
pyproject.toml             # uv dependencies
.env.example               # safe local env template
.env                       # local secrets (gitignored)
.github/workflows/
  daily_news.yml           # CI: astral-sh/setup-uv + uv sync + uv run src/pipelines/email_pipeline.py
```

## Module responsibilities

| Module | Key functions |
|---|---|
| `core/config.py` | `RSS_SOURCES`, `STOCK_RSS_FEEDS`, `STOCK_INDICES`, env var constants, `CATEGORY_EMOJIS`, `CATEGORY_ZH_TO_RSS`, `BACKEND`, `MODEL`, `MAX_RETRIES` |
| `core/rss.py` | `extract_image_url(entry)` — tries media_content → media_thumbnail → HTML img parse; `fetch_rss_articles(category, feeds, hours=24)` — fetches RSS, filters to last 24h |
| `core/llm_client.py` | `generate_summary(all_articles, stock_articles=None, stock_snapshot='')` — loads prompt from `prompts/email_digest.md`; `BACKEND=BEDROCK_CLAUDE`, `CLAUDE_API`, `CLAUDE_CLI`, or `CODEX_CLI`; all paths parse text JSON with `json_repair` fallback and up to `MAX_RETRIES` attempts |
| `core/digest.py` | `resolve_references(parsed_json, all_articles)` maps normal section refs; `resolve_market_pulse(parsed_json, stock_articles)` maps market-pulse refs |
| `core/renderer.py` | `build_email_html_from_json(sections, gas_prices=None, stock_indices=None, market_pulse=None)` — renders full HTML document using `templates/email.html` |
| `core/gas_prices.py` | `fetch_all_gas_prices()` — Vancouver predictions + Seattle prices |
| `core/stock_market.py` | `fetch_stock_indices()` and `format_snapshot_for_prompt()` — CNBC quote snapshot for configured US indices |
| `core/mailer.py` | `send_email_gmail(subject, body_html, recipients)` — Gmail SMTP with App Password is the configured path; Gmail API via OAuth2 remains available if explicitly configured |

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

## Market pulse

The email pipeline fetches `STOCK_RSS_FEEDS` separately from the five regular categories. These articles are fed only to the LLM backend's `market_pulse` output and are resolved by number against the stock article list. They are not rendered as regular digest items.

`STOCK_INDICES` configures CNBC quote symbols for the index snapshot currently rendered above the news sections. If the stock feeds and CNBC snapshot are both unavailable, the prompt tells Claude to set `market_pulse` to `null`.

## Image extraction coverage

- `media_content`: Guardian
- `media_thumbnail`: BBC
- HTML `<img>` parse from `entry.content`: The Verge

## Env vars

```
# Email pipeline
AWS_REGION=us-east-1      # required for BACKEND=BEDROCK_CLAUDE
ANTHROPIC_API_KEY=        # required only for BACKEND=CLAUDE_API
GMAIL_USER=              # sender Gmail address
GMAIL_APP_PASSWORD=      # 16-char Gmail App Password, current GitHub Actions email path
EMAIL_TO=                # comma-separated recipients

# Optional / not currently configured in GitHub Actions
GMAIL_CLIENT_ID=         # Gmail API mode
GMAIL_CLIENT_SECRET=     # Gmail API mode
GMAIL_REFRESH_TOKEN=     # Gmail API mode

# Telegram pipeline
OPENCLAW_CONFIG=         # absolute path to openclaw.json
TELEGRAM_CHAT_ID=        # Telegram chat/channel ID

# Shared LLM backend
BACKEND=BEDROCK_CLAUDE   # BEDROCK_CLAUDE, CLAUDE_API, CLAUDE_CLI, or CODEX_CLI
MODEL=                   # optional; backend model/alias. Defaults: Bedrock Claude uses us.anthropic.claude-haiku-4-5-20251001-v1:0, Claude API uses claude-haiku-4-5-20251001, Claude CLI uses haiku, Codex CLI uses its own configured default. Set explicitly for Codex-backed testing, e.g. gpt-5.4-mini

# Local dev / testing
MODE=TEST                # optional; limits test scripts to 1 article per category (faster, fewer tokens)
```

GitHub Actions (email pipeline): `BACKEND`, `AWS_REGION`, and `MODEL` come from Actions Variables. AWS OIDC role comes from the `AWS_ROLE_ARN` Secret; `GMAIL_USER`, `GMAIL_APP_PASSWORD`, and `EMAIL_TO` are also Secrets. Gmail API credentials are not needed for the current GA setup.

## Local dev workflow

```bash
uv sync                                      # install deps
uv run pytest                               # unit tests
uv run tests/test_rss.py                     # check feeds
uv run tests/test_llm.py                     # test configured LLM output + generate preview
open generated/preview.html                  # inspect email layout in browser
uv run tests/test_email.py                   # send preview via Gmail
uv run src/pipelines/email_pipeline.py       # full run including email
```

## Cost (approximate)

| Model | Per run | Per month (1×/day) |
|---|---|---|
| Haiku 4.5 | ~$0.014 | ~$0.42 |
| Sonnet 4.5 | ~$0.053 | ~$1.60 |

Current model: Claude Haiku 4.5 via AWS Bedrock in GitHub Actions.
