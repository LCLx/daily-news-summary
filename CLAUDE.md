# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Two parallel pipelines, both fetching from the same RSS sources (`RSS_SOURCES` in `src/email_pipeline.py`):
- **Email pipeline** (`src/email_pipeline.py`): RSS → Claude API → HTML email via Gmail SMTP. Runs on GitHub Actions daily at 08:00 PST (UTC 16:00).
- **Telegram pipeline** (`src/telegram_pipeline.py`): RSS → Claude CLI (subscription, not API) → Telegram message.

## Commands

```bash
uv sync                              # install dependencies
uv run src/email_pipeline.py             # email pipeline: fetch → summarize → email
uv run src/telegram_pipeline.py                  # telegram pipeline: fetch → summarize → telegram
uv run tests/test_rss.py             # check RSS feed reachability + article counts
uv run tests/test_claude.py          # Claude pipeline test, saves generated/preview.html (no email)
uv run tests/test_email.py           # send last generated preview via Gmail (run test_claude.py first)
uv run tests/test_integration.py     # end-to-end: RSS → Claude → email
```

Tests are standalone scripts (not pytest). Each is run directly with `uv run`. Test scripts import from `src/` via `sys.path.insert`. The `generated/` directory is gitignored and holds `preview.html` output.

## Architecture

**Single-file pipeline** (`src/email_pipeline.py`):
1. `fetch_rss_articles()` — fetches RSS, filters to last 24h (UTC), extracts images via `extract_image_url()`
2. `generate_summary_with_claude()` — builds a Chinese-language prompt, calls Claude API, returns structured JSON with article refs (e.g. `"Tech & AI:3"`) instead of full text to minimize output tokens
3. `resolve_references()` — maps Claude's JSON article refs back to full RSS article data (URL, image, source, etc.)
4. `build_email_html_from_json()` — renders resolved sections to a styled HTML email using stdlib `html.escape()` (XSS-safe)
5. `send_email_gmail()` — delivers via Gmail SMTP with App Password
6. `main()` — orchestrates the pipeline

RSS sources are defined in `RSS_SOURCES` dict at module level, grouped by 5 categories: Tech & AI, Global Affairs, Business & Finance, Pacific Northwest, Health & Science.

Image extraction tries multiple strategies in order: `media_thumbnail` → `media_content` → `<img>` in content HTML → `<img>` in summary HTML.

## Environment variables

Required in `.env` for local dev (loaded via `python-dotenv`):
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
