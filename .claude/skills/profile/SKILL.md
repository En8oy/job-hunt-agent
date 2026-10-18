---
name: profile
description: Create or update me/profile.yml — search titles, seniority, modality and cities, salary expectation, languages, platforms and screening defaults — inferred from the user's CV and confirmed with them. Use for /profile, during /setup, or when the user wants to change job titles, salary, target cities or platforms.
---

# /profile

Fill `me/profile.yml` (structure: `profile.example.yml`). Infer everything you can from
`me/cv_*.md`, and ask only what the CV can't tell you. Talk in the user's language.
If `me/profile.yml` already exists, show the current values for each part and ask what to
change instead of starting over. Keep `disclaimer_accepted_at` exactly as it is.

## 1. Propose from the CV

From the CV, work out: name and contact, location and time zone, years of experience,
likely seniority, core stack, domain, languages. Show it as a short summary and ask the
user to confirm or correct.

## 2. Search titles

Generate the titles the search agents will type into each site. Mix:
- **priority:** the 3–5 titles that best match their real experience at the seniority they
  want now (e.g. "Semi Senior Full Stack Developer", "Mid-Level Laravel Developer").
- **local_language:** the same roles as written in the local market, if it isn't English
  ("Desarrollador Full Stack", "Programador PHP", "Ingeniero de Software").
- **adjacent:** nearby roles their experience supports (e.g. "AI Engineer" only if they
  have real hands-on AI/LLM work; "Frontend Developer" for a full stack dev who is strong
  on frontend).
- **general:** broader titles to widen the net, senior variants last.

Explain each group in one line and let the user add, remove or reorder (AskUserQuestion
with multiSelect works well). Also ask what to **avoid** (stacks, roles, industries).

## 3. Ask what the CV doesn't say

In small batches:
- Seniority priority and any strategy for now (e.g. "prioritize Spanish-speaking roles
  while I improve my English interviews").
- Modality: remote only, or also hybrid/on-site — and in which cities exactly.
- Target markets (country/region) and work authorization.
- **Expected salary**: amount, currency and period, the number they want typed into
  forms. Offer the market context you know, but the number is theirs to choose.
- Notice period / availability start, relocation.
- Honest language levels (the agents will repeat these on forms).
- Real skills that aren't on the CV but they're comfortable mentioning, and things they
  must never claim.
- Email for recruiter replies and which webmail (Outlook, Gmail...).
- Platforms: list the files in `platforms/` with a one-line note each, and ask where they
  have an account and which to enable. Mark `account: true` only where they confirm one,
  because agents never create accounts.
- Rules: actually submit, or stop before the final button? How many applications per
  platform per run? Should agents ask them about opinion questions?

## 4. Save

Write `me/profile.yml`, keeping the example's structure and comments. Show the final
search titles, salary, modality and enabled platforms in a short summary.
