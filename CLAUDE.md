# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Two parallel pipelines, both fetching from the same RSS sources (`RSS_SOURCES` in `src/core/config.py`):
- **Email pipeline** (`src/pipelines/email_pipeline.py`): RSS + gas prices → Claude CLI → HTML email via Gmail API (OAuth2).
- **Telegram pipeline** (`src/pipelines/telegram_pipeline.py`): RSS → Claude CLI → Telegram message.

## Commands

```bash
uv sync                                        # install dependencies
uv run src/pipelines/email_pipeline.py         # email pipeline: fetch → summarize → email
uv run src/pipelines/telegram_pipeline.py      # telegram pipeline: fetch → summarize → telegram
uv run tests/test_rss.py                       # check RSS feed reachability + article counts
uv run tests/test_claude.py                    # generate digest + save preview (no email)
uv run tests/test_email.py                     # send last generated preview via Gmail (run test_claude.py first)
uv run tests/test_integration.py               # end-to-end: full pipeline including email
```

Tests are standalone scripts (not pytest). Each is run directly with `uv run`. `test_claude.py` and `test_integration.py` import from `email_pipeline` directly (`generate_digest`, `save_preview`, `main`). The `generated/` directory is gitignored and holds `preview.html` and `preview.json` output.

## Architecture

```
src/
  core/                    # shared modules
    config.py              # RSS_SOURCES, DEALS_BLOCKED_KEYWORDS, env vars, CATEGORY_EMOJIS, CATEGORY_ZH_TO_RSS, CLAUDE_MAX_RETRIES
    rss.py                 # extract_image_url(), fetch_rss_articles() — Deals category applies DEALS_BLOCKED_KEYWORDS filter
    claude_client.py       # generate_summary_with_claude() — Claude CLI (claude -p) + json_repair
    digest.py              # resolve_references() — maps Claude JSON refs to full article data
    renderer.py            # build_email_html_from_json() — renders sections to HTML
    gas_prices.py          # fetch_all_gas_prices() — Vancouver (gaswizard.ca) + Seattle (AAA)
    mailer.py              # send_email_gmail() — Gmail API (OAuth2) delivery
  pipelines/               # entry points
    email_pipeline.py      # generate_digest() → save_preview() → send_email(); main() runs all three
    telegram_pipeline.py   # telegram pipeline
  prompts/
    email_digest.md        # Claude prompt template ($articles placeholder)
  templates/
    email.html             # HTML email wrapper/CSS ($date_str, $body_html placeholders)
```

Both pipelines share `src/core/`. Test scripts add `src/` to `sys.path` and import via `core.*`.

**Pipeline flow:**
1. `fetch_rss_articles()` — fetches RSS, filters to last 24h (UTC), extracts images via `extract_image_url()`, drops Deals articles matching `DEALS_BLOCKED_KEYWORDS` (checks title + link + summary, handles both spaces and hyphens)
2. `fetch_all_gas_prices()` — scrapes Vancouver gas price predictions from gaswizard.ca and Seattle metro current averages from AAA; returns list of city dicts (gracefully skips on failure)
3. `generate_summary_with_claude()` — loads prompt from `prompts/email_digest.md`, calls Claude CLI (`claude -p`) with `json_repair` fallback, returns structured JSON with number-only article refs (e.g. `"3"`) to minimize output tokens
4. `resolve_references()` — maps Claude's JSON refs back to full RSS article data (URL, image, source, etc.)
5. `build_email_html_from_json()` — renders resolved sections using `templates/email.html` and stdlib `html.escape()` (XSS-safe); appends gas price cards at the end if available
6. `send_email_gmail()` — delivers via Gmail REST API (OAuth2)

RSS sources are defined in `RSS_SOURCES` in `src/core/config.py`, grouped by 6 categories: Tech & AI, Global Affairs, Business & Finance, Pacific Northwest, Health & Science, Deals.

Image extraction tries multiple strategies in order: `media_content` → `media_thumbnail` → `<img>` in content HTML → `<img>` in summary HTML.

## Environment variables

Required in `.env` for local dev (loaded via `python-dotenv` in `config.py`):
- `GMAIL_USER`, `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, `EMAIL_TO` — email pipeline
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — telegram pipeline
- `CLAUDE_CLI_MODEL` — CLI model alias (e.g. `haiku`), used by both pipelines (default: `haiku`)
- `MODE=TEST` — optional; limits to 1 article per category in pipeline (faster, fewer tokens)

## Conventions

- **Language:** code comments in English; user-facing output (print statements, email content, Claude prompts) in Chinese
- **Package manager:** uv only (pyproject.toml, no requirements.txt)
- **No test framework:** tests are plain Python scripts run with `uv run`
- **Phase 2 (planned):** multi-user support via Supabase + FastAPI — see `docs/REQUIREMENTS.md`
