# Requirements

## Phase 1 — Completed

**Goal:** Daily automated news digest — fetch RSS, summarize in Chinese via Claude, deliver by email.

### Implemented

- **RSS fetching:** 5 categories (Tech & AI, Global Affairs, Business & Finance, Pacific Northwest, Health & Science), 12 sources total
- **Time filtering:** articles from the last 24 hours only
- **Image extraction:** multi-strategy (media_thumbnail → media_content → HTML img tag)
- **Claude summarization:** Anthropic API, Chinese markdown output
- **HTML email:** markdown rendered to styled HTML, delivered via Gmail SMTP
- **Scheduled automation:** GitHub Actions, daily at 08:00 PST
- **Tests:** RSS reachability check + Claude pipeline preview
- **Cost optimization:** Haiku model, ~$0.014/run, ~$0.42/month

---

## Phase 2 — Planned

**Goal:** Multi-user support — users log in with email OTP, customize RSS sources and prompt per account.

### Implemented

- **Email OTP login:** two-step flow (enter email → receive code → verify), handled by Supabase Auth
- **Settings page:** users can edit RSS URLs per category and add custom prompt instructions
- **Per-user email delivery:** GitHub Actions iterates over all active users, generates and sends a personalized digest for each
- **Backward compatibility:** falls back to single-user mode when Supabase env vars are not set
- **Deployment:** web app on Railway, GitHub Actions still handles daily scheduling

### New stack

- Supabase (PostgreSQL + Auth)
- FastAPI + Jinja2 (settings web app)
- Railway (web app hosting)

### New files

- [web/main.py](web/main.py) — FastAPI app (login + settings routes)
- [web/templates/login.html](web/templates/login.html) — login page
- [web/templates/settings.html](web/templates/settings.html) — settings page
- [Procfile](Procfile) — Railway start command

### Supabase schema

```sql
CREATE TABLE user_configs (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
  rss_sources jsonb NOT NULL DEFAULT '{}',
  custom_prompt text,
  is_active   boolean NOT NULL DEFAULT true,
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now()
);
ALTER TABLE user_configs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own config" ON user_configs
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
```

### Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `SUPABASE_URL` | Actions + Railway | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Actions only | Server-side key, bypasses RLS |
| `SUPABASE_ANON_KEY` | Railway | Client-side key for web app |
| `SECRET_KEY` | Railway | Signs session cookies |

---

## Phase 3 — To be defined

<!-- Add Phase 3 requirements here -->
