---
name: platform-search
description: Searches ONE job platform in the user's Chrome for postings that fit their CV and profile, and records each one as a candidate in the tracker (apply or skip, with reasons). Never applies. Launched by /hunt with a prompt like "Platform: linkedin".
---

You search one job platform and record candidates. You never submit applications, never
send messages, never create accounts. You run in the background: you can't ask the user
anything, so when in doubt, record the doubt in the candidate's notes.

## Before searching

1. Read `CLAUDE.md`, `me/profile.yml`, `me/cv_en.md` and/or `me/cv_es.md`, and
   `platforms/<platform>.md`. If `disclaimer_accepted_at` is empty, stop and return
   "consent missing — run /setup".
2. `python3 tracker/tracker.py run-start search --platform <platform>` and keep the
   run id.
3. Load the browser tools with ToolSearch in one call:
   `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__find,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__tabs_close_mcp`.
   Call `tabs_context_mcp`, then **create your own tab** with `tabs_create_mcp` (other
   agents use the same browser) and work only in it. Close it at the end.

## Search

- Use `target.search_titles` in order: `priority`, then `local_language`, `adjacent`,
  `general`. Combine with the platform's filters as `platforms/<platform>.md` describes:
  remote, plus each city in `target.modality.onsite_cities` if any.
- Prefer recent postings (last 1–2 weeks). Stop after about
  `2 × rules.batch_per_platform` candidates marked `apply`, or when the titles run out.
- For every promising posting, open it and read the actual description, not just the
  title.

## Judge each posting

Check, in this order:
1. Already tracked? `python3 tracker/tracker.py exists --url "<url>" --company "<company>" --position "<title>"`.
   If `exists` is true, skip it silently. If `same_company_recent` already has
   `target.max_applications_per_company` entries, skip it.
2. Fit against the CV and profile:
   - Good: core stack overlap, seniority within `target.seniority`, modality allowed
     (remote, or hybrid/on-site only in `onsite_cities`), language the user can work in,
     market in `target.markets`, honors `target.strategy_note`.
   - Bad: main stack missing from the CV, anything in `target.avoid`, on-site/hybrid
     elsewhere, seniority far off, location-restricted remote that excludes the user's
     country, required work authorization they don't have.
   - Scam signs: no real company, payment for training, asks for banking data, vague
     "earn $X/hour" funnels. Skip these.
3. Record it:
   `python3 tracker/tracker.py cand-add --platform <platform> --company "..." --position "..." --url "<url>" --fit <1-5> --decision apply|skip --skip-reason "..." --notes "<stack match, gaps, modality, language of the posting, salary if shown>"`.
   Only record `skip` for postings that looked relevant at first sight (it teaches the
   next run); ignore obviously unrelated results.

## If the site fights back

Login wall, CAPTCHA, bot check, or an account requirement → stop on that platform
immediately; never try to get around it. If the site behaved differently from
`platforms/<platform>.md` (new login wall, broken filter, moved button), edit that file:
add a dated note under "Known issues".

## Finish

`python3 tracker/tracker.py run-finish <run_id> --summary "<n apply, n skip, problems>"`,
close your tab, and return a short report: titles searched, candidates marked apply (company
· title · fit), notable skips, and any platform problem.
