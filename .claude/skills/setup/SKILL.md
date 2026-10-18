---
name: setup
description: First-run onboarding for job-hunt-agent. Shows the automation warning and records consent, checks requirements, builds or reviews the CV, creates me/profile.yml and the database. Resumable — run it again and it continues where it stopped. Use when the user runs /setup, is new to the repo, or asks how to get started.
---

# /setup

Walk the user through getting ready, one stage at a time. Talk in the user's language
(ask once if unclear: "¿Prefieres español o inglés? / Spanish or English?").

**First, detect what's already done** and skip finished stages, telling the user what
you found ("Ya aceptaste el aviso el 2026-10-18 y tu CV está listo; sigo con el perfil."):

| Stage | Done when |
|---|---|
| 1. Warning | `me/profile.yml` exists and `disclaimer_accepted_at` is set |
| 2. Requirements | always re-check (it's quick) |
| 3. CV | `me/cv_en.md` or `me/cv_es.md` exists and the user approved it |
| 4. Profile | `me/profile.yml` has non-empty `target.search_titles` and `screening_defaults.expected_salary.amount` |
| 5. Database | `me/data/job_search.db` exists |

## 1. Warning and consent

Show this warning in full, in the user's language, and ask for an explicit yes
(use AskUserQuestion with "Acepto / I accept" and "No por ahora / Not now"):

> **Antes de empezar**
> - Estos agentes envían **aplicaciones reales a tu nombre**, usando tu navegador y las
>   cuentas en las que ya iniciaste sesión.
> - Automatizar postulaciones puede ir **contra los términos de uso** de LinkedIn, Indeed
>   y otros sitios. Existe el riesgo de que limiten o suspendan tu cuenta. Úsalo con
>   moderación (`rules.batch_per_platform` en tu perfil).
> - Los agentes nunca inventan experiencia, pero **tú eres responsable** de revisar tu
>   CV, tu perfil y lo que se envía. Revisa el dashboard con frecuencia.
> - Nunca resuelven CAPTCHAs, nunca crean cuentas, nunca meten datos de pago y nunca
>   responden mensajes por ti.
> - Tus datos (CV, perfil, base de datos) se quedan en tu máquina, en la carpeta `me/`,
>   que git ignora. Lo que sí sale de tu máquina: lo que los agentes escriben en los
>   sitios de empleo y lo que Claude procesa para hacer el trabajo.

> **Before you start**
> - These agents submit **real job applications in your name**, using your browser and
>   the accounts you're already signed into.
> - Automating applications may **violate the terms of service** of LinkedIn, Indeed and
>   other sites, and your account could be limited or suspended. Use it in moderation
>   (`rules.batch_per_platform` in your profile).
> - The agents never invent experience, but **you are responsible** for reviewing your CV,
>   your profile and what gets sent. Check the dashboard often.
> - They never solve CAPTCHAs, create accounts, enter payment details, or reply to
>   messages for you.
> - Your data (CV, profile, database) stays on your machine in `me/`, which git ignores.
>   What does leave it: what the agents type into job sites, and what Claude processes to
>   do the work.

- If they decline: stop here. Explain they can still use `/cv-review` or `/cv-interview`
  to fix their CV without any automation, and can run `/setup` again later.
- If they accept: copy `profile.example.yml` to `me/profile.yml` if it doesn't exist, and
  set `disclaimer_accepted_at` to the current date-time (ISO, local time). Never set it
  without an explicit yes in this conversation.

## 2. Requirements

Check and report in one short list:
- Python 3.9+: `python3 --version`.
- Chrome/Chromium for PDFs: `python3 tools/render_cv.py --check`.
- Claude in Chrome: load the browser tools with ToolSearch
  (`select:mcp__claude-in-chrome__tabs_context_mcp`) and call `tabs_context_mcp`. If the
  tools don't exist or the call fails, explain how to install the extension
  (https://claude.ai/chrome) and connect it, and note that stages 3–5 still work without it;
  only `/hunt` and `/check-email` need it.

Don't block on a missing browser extension; do block on missing Python.

## 3. CV

Look in `me/cv_original/` and `me/cv_*.md`:
- `me/cv_*.md` already exists → ask whether to keep it, review it again (`/cv-review`) or
  skip.
- Files in `me/cv_original/` → run the `cv-review` skill.
- Nothing → ask: "¿Tienes un CV que puedas poner en `me/cv_original/`, o prefieres que lo
  armemos platicando?" Then run `cv-review` (after they drop the file) or `cv-interview`.

Invoke those skills with the Skill tool and follow them fully before continuing.

## 4. Profile

Run the `profile` skill.

## 5. Database and next steps

Run `python3 tracker/tracker.py pending` (this creates the database on first use) and
finish with a short "what now" in the user's language:

- `/hunt` — search the enabled platforms and apply (`/hunt linkedin` for just one).
- `/check-email` — read recruiter replies and log them.
- `/dashboard` — open the dashboard.
- `/cv-review`, `/profile` — update the CV or the search profile anytime.

Remind them to upload the new `me/cv_*.pdf` to the CV slots stored on each job site
(LinkedIn, Indeed, etc.); those copies don't update by themselves.
