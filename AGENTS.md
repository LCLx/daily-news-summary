# AGENTS.md

Guidance for Codex and other AI coding agents working in this repository.

## Shared Context

Read `docs/CONTEXT.md` before making non-trivial changes. It is the neutral project knowledge base shared across assistants. `CLAUDE.md` contains Claude Code-specific guidance and should stay aligned with the shared context.

When project architecture, commands, environment variables, or conventions change, update `docs/CONTEXT.md` first. Then update `CLAUDE.md` or this file only if the tool-specific guidance also needs to change.

## Quick Reference

- Package manager: `uv` only.
- Unit tests use pytest under `tests/unit`; integration/check scripts are run directly with `uv run`.
- Useful commands:

```bash
uv sync
uv run pytest
uv run tests/test_rss.py
uv run tests/test_claude.py
uv run tests/test_email.py
uv run tests/test_integration.py
uv run src/pipelines/email_pipeline.py
uv run src/pipelines/telegram_pipeline.py
```

- Generated previews live under `generated/` and are gitignored.
- Code comments should be in English.
- User-facing output, email content, Telegram content, and summarization prompts should be in Chinese.
- Shared modules live in `src/core/`; pipeline entry points live in `src/pipelines/`.
- RSS sources are configured in `src/core/config.py`.
- Email prompt is `src/prompts/email_digest.md`.
- Email HTML wrapper is `src/templates/email.html`.

## Safety Notes

- Do not commit or print secrets from `.env`.
- Preserve unrelated user changes in the working tree.
- Prefer focused edits that follow the existing pipeline structure.
