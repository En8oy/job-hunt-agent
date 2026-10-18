# job-hunt-agent

A job-search toolkit run entirely by Claude Code on the user's own machine: it turns their CV
into an ATS-ready one, builds a search profile, searches job platforms in their own browser
(Claude in Chrome), applies, checks email for replies, and tracks everything in SQLite.

Talk to the user in the language they write in. Files under `.claude/`, `platforms/` and
`tracker/` are in English; CVs and answers follow the job posting's language.

## Where things are

- `me/` — the user's private data, git-ignored: `cv_original/`, `cv_en.md`/`cv_es.md`
  (source of truth for the CV), PDFs, `profile.yml`, `data/job_search.db`.
- `tracker/tracker.py` — the only way to read or write the database. JSON output; see `-h`.
- `tracker/dashboard.py` — local dashboard on http://127.0.0.1:8765.
- `tools/render_cv.py` — Markdown CV → ATS-friendly PDF via headless Chrome.
- `platforms/<name>.md` — how to search and apply on each site, with known pitfalls.
- `.claude/skills/` — interactive commands: `/setup`, `/cv-review`, `/cv-interview`,
  `/profile`, `/hunt`, `/check-email`, `/dashboard`.
- `.claude/agents/` — background workers: `platform-search`, `applier`, `email-checker`.

## Rules that always apply

1. **Never invent anything about the user.** Every claim in a CV, form or screening answer
   must come from `me/cv_*.md`, `me/profile.yml` or something the user said in chat. If a
   required field needs a fact you don't have, don't guess: leave the application as
   `needs_info` and add a task explaining what's missing.
2. **Gate on consent.** Searching, applying and reading email require
   `disclaimer_accepted_at` to be set in `me/profile.yml`. If it isn't, stop and tell the
   user to run `/setup`.
3. **Hard limits:** never solve or bypass a CAPTCHA or bot check, never create an account
   on any site, never enter payment or banking details, never reply to recruiters or send
   messages on the user's behalf, never re-process a job already in the tracker.
4. **Opinion questions** ("why do you want to work here?", "describe your ideal team") are
   the user's to answer when `rules.ask_on_opinion_questions` is true: ask them in chat
   rather than writing an answer for them.
5. **Database access goes through `tracker/tracker.py` only.** No raw SQL, no editing the
   `.db` file, no copying it while agents run.
6. **CV language:** send the CV in the language the job posting is written in.
7. When a platform behaves differently from what `platforms/<name>.md` says (new login
   wall, broken filter, changed flow), update that file with the date and what you saw.
