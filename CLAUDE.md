# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Two parallel pipelines, both fetching from the same RSS sources (`RSS_SOURCES` in `src/core/config.py`):
- **Email pipeline** (`src/pipelines/email_pipeline.py`): RSS → Claude API → HTML email via Gmail SMTP. Runs on GitHub Actions daily at 08:00 PST (UTC 16:00).
- **Telegram pipeline** (`src/pipelines/telegram_pipeline.py`): RSS → Claude CLI (subscription, not API) → Telegram message.

## Commands

```bash
uv sync                                        # install dependencies
uv run src/pipelines/email_pipeline.py         # email pipeline: fetch → summarize → email
uv run src/pipelines/telegram_pipeline.py      # telegram pipeline: fetch → summarize → telegram
uv run tests/test_rss.py                       # check RSS feed reachability + article counts
uv run tests/test_claude.py                    # Claude pipeline test, saves generated/preview.html (no email)
uv run tests/test_email.py                     # send last generated preview via Gmail (run test_claude.py first)
uv run tests/test_integration.py               # end-to-end: RSS → Claude → email
```

Tests are standalone scripts (not pytest). Each is run directly with `uv run`. Test scripts import from `src/` via `sys.path.insert`. The `generated/` directory is gitignored and holds `preview.html` and `preview.json` output.

## Architecture

```
src/
  core/                    # shared modules
    config.py              # RSS_SOURCES, env vars, CATEGORY_EMOJIS, CLAUDE_MAX_RETRIES
    rss.py                 # extract_image_url(), fetch_rss_articles()
    claude_client.py       # generate_summary_with_claude() — API tool calling / CLI + json_repair
    digest.py              # resolve_references() — maps Claude JSON refs to full article data
    renderer.py            # build_email_html_from_json() — renders sections to HTML
    mailer.py              # send_email_gmail() — Gmail SMTP delivery
  pipelines/               # entry points
    email_pipeline.py      # main() — orchestrates the email pipeline
    telegram_pipeline.py   # telegram pipeline
  prompts/
    email_digest.md        # Claude prompt template ($articles placeholder)
  templates/
    email.html             # HTML email wrapper/CSS ($date_str, $body_html placeholders)
```

Both pipelines share `src/core/`. Test scripts add `src/` to `sys.path` and import via `core.*`.

**Pipeline flow:**
1. `fetch_rss_articles()` — fetches RSS, filters to last 24h (UTC), extracts images via `extract_image_url()`
2. `generate_summary_with_claude()` — loads prompt from `prompts/email_digest.md`, calls Claude (API: tool calling for guaranteed valid JSON; CLI: text output with `json_repair` fallback), returns structured JSON with article refs (e.g. `"Tech & AI:3"`) to minimize output tokens
3. `resolve_references()` — maps Claude's JSON refs back to full RSS article data (URL, image, source, etc.)
4. `build_email_html_from_json()` — renders resolved sections using `templates/email.html` and stdlib `html.escape()` (XSS-safe)
5. `send_email_gmail()` — delivers via Gmail SMTP with App Password

RSS sources are defined in `RSS_SOURCES` in `src/core/config.py`, grouped by 6 categories: Tech & AI, Global Affairs, Business & Finance, Pacific Northwest, Health & Science, Deals.

Image extraction tries multiple strategies in order: `media_content` → `media_thumbnail` → `<img>` in content HTML → `<img>` in summary HTML.

## Environment variables

Required in `.env` for local dev (loaded via `python-dotenv` in `config.py`):
- `ANTHROPIC_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `EMAIL_TO` — email pipeline
- `OPENCLAW_CONFIG`, `CLAUDE_MODEL`, `TELEGRAM_CHAT_ID` — telegram pipeline
- `CLAUDE_MODEL` is shared by both pipelines
- `CLAUDE_BACKEND=cli` — use Claude CLI subprocess instead of API (for local dev with subscription)
- `MODE=TEST` — optional; limits test scripts to 1 article per category (faster, fewer tokens)

## Conventions

- **Language:** code comments in English; user-facing output (print statements, email content, Claude prompts) in Chinese
- **Package manager:** uv only (pyproject.toml, no requirements.txt)
- **No test framework:** tests are plain Python scripts run with `uv run`
- **Phase 2 (planned):** multi-user support via Supabase + FastAPI — see `docs/REQUIREMENTS.md`
