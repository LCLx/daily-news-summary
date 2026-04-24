# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Two parallel pipelines, both fetching from the shared RSS source config (`RSS_SOURCES` in `src/core/config.py`):
- **Email pipeline** (`src/pipelines/email_pipeline.py`): RSS + gas prices + US market data → configured LLM backend → HTML email via Gmail SMTP/App Password. Runs on GitHub Actions daily.
- **Telegram pipeline** (`src/pipelines/telegram_pipeline.py`): RSS → Claude CLI (subscription, not API) → Telegram message.

## Commands

```bash
uv sync                                        # install dependencies
uv run src/pipelines/email_pipeline.py         # email pipeline: fetch → summarize → email
uv run src/pipelines/telegram_pipeline.py      # telegram pipeline: fetch → summarize → telegram
uv run tests/test_rss.py                       # check RSS feed reachability + article counts
uv run tests/test_llm.py                       # generate digest + save preview (no email)
uv run tests/test_email.py                     # send last generated preview via Gmail (run test_llm.py first)
uv run tests/test_integration.py               # end-to-end: full pipeline including email
```

Unit tests live under `tests/unit` and are run with `uv run pytest`. Older integration/check scripts are still run directly with `uv run`. `test_llm.py` and `test_integration.py` import from `email_pipeline` directly (`generate_digest`, `save_preview`, `main`). The `generated/` directory is gitignored and holds `preview.html` and `preview.json` output.

## Architecture

```
src/
  core/                    # shared modules
    config.py              # RSS_SOURCES, env vars, CATEGORY_EMOJIS, CATEGORY_ZH_TO_RSS, BACKEND, MODEL, MAX_RETRIES
    rss.py                 # extract_image_url(), fetch_rss_articles()
    llm_client.py          # generate_summary() — Bedrock Claude, Claude API, Claude CLI, or Codex CLI with json_repair fallback
    digest.py              # resolve_references() — maps LLM JSON refs to full article data
    renderer.py            # build_email_html_from_json() — renders sections to HTML
    gas_prices.py          # fetch_all_gas_prices() — Vancouver (gaswizard.ca) + Seattle (AAA primary, EIA fallback)
    stock_market.py        # fetch_stock_indices() — CNBC quote snapshot for market pulse
    mailer.py              # send_email_gmail() — Gmail SMTP/App Password path used in GA; Gmail API support retained
  pipelines/               # entry points
    email_pipeline.py      # generate_digest() → save_preview() → send_email(); main() runs all three
    telegram_pipeline.py   # telegram pipeline
  prompts/
    email_digest.md        # digest prompt template ($articles, $stock_block placeholders)
  templates/
    email.html             # HTML email wrapper/CSS ($date_str, $body_html placeholders)
```

Both pipelines share `src/core/`. Test scripts add `src/` to `sys.path` and import via `core.*`.

**Pipeline flow:**
1. `fetch_rss_articles()` — fetches regular-category RSS, filters to last 24h (UTC), extracts images via `extract_image_url()`
2. `fetch_all_gas_prices()` — scrapes Vancouver gas price predictions from gaswizard.ca and Seattle-Bellevue-Everett daily averages from AAA, falling back to EIA weekly data if AAA is unreachable; each city dict carries a `source_name` the renderer uses for attribution
3. `fetch_stock_indices()` — fetches the CNBC quote snapshot for configured US indices; `STOCK_RSS_FEEDS` provides separate stock-market articles for the `market_pulse`
4. `generate_summary()` — loads prompt from `prompts/email_digest.md`, calls the configured LLM backend (`BACKEND=BEDROCK_CLAUDE`, `CLAUDE_API`, `CLAUDE_CLI`, or `CODEX_CLI`), returns structured JSON with normal `sections` and optional `market_pulse`
5. `resolve_references()` and `resolve_market_pulse()` — map LLM number-only refs back to full RSS article data
6. `build_email_html_from_json()` — renders market pulse, resolved news sections, and gas price cards using `templates/email.html` and stdlib `html.escape()` (XSS-safe)
7. `send_email_gmail()` — delivers via Gmail SMTP with App Password in GitHub Actions; Gmail API support remains available if OAuth2 credentials are explicitly configured

RSS sources are defined in `RSS_SOURCES` in `src/core/config.py`, grouped by 5 categories: Tech & AI, Global Affairs, Business & Finance, Pacific Northwest, Health & Science.
Stock market sources and quote symbols are defined in `STOCK_RSS_FEEDS` and `STOCK_INDICES`.

Image extraction tries multiple strategies in order: `media_content` → `media_thumbnail` → `<img>` in content HTML → `<img>` in summary HTML.

## Environment variables

Required in `.env` for local dev (loaded via `python-dotenv` in `config.py`):
- `AWS_REGION`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `EMAIL_TO` — email pipeline (current GitHub Actions path uses AWS OIDC + Bedrock Claude)
- `ANTHROPIC_API_KEY` — required only for `BACKEND=CLAUDE_API`
- `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` — optional Gmail API delivery mode, not currently configured in GitHub Actions
- `OPENCLAW_CONFIG`, `MODEL`, `TELEGRAM_CHAT_ID` — telegram pipeline
- `BACKEND=BEDROCK_CLAUDE|CLAUDE_API|CLAUDE_CLI|CODEX_CLI` — email summary backend
- `MODEL` — optional backend model/alias. Defaults: Bedrock Claude uses `us.anthropic.claude-haiku-4-5-20251001-v1:0`, Claude API uses `claude-haiku-4-5-20251001`, Claude CLI uses `haiku`, Codex CLI uses its own configured default if unset. For Codex-backed testing, set this explicitly, for example `gpt-5.4-mini`.
- `MODE=TEST` — optional; limits to 1 article per category in pipeline (faster, fewer tokens)

## Conventions

- **Language:** code comments in English; user-facing output (print statements, email content, LLM prompts) in Chinese
- **Package manager:** uv only (pyproject.toml, no requirements.txt)
- **Tests:** unit tests use pytest under `tests/unit`; older integration scripts are plain Python scripts run directly with `uv run`
- **Phase 2 (planned):** multi-user support via Supabase + FastAPI — see `docs/REQUIREMENTS.md`
