---
name: cv-interview
description: Build an ATS-ready CV from scratch by interviewing the user conversationally, section by section, then write me/cv_en.md and/or me/cv_es.md and render the PDFs. Use for /cv-interview, when the user has no CV, or says "ayúdame a hacer mi CV" / "build my resume with me".
---

# /cv-interview

Interview the user and write their CV. Same output, structure and rules as `/cv-review`:
read `../cv-review/references/ats-guidelines.md` and `../cv-review/references/cv-template.md`
first. Talk in the user's language, warmly and briefly. This is a conversation, not a form.

## How to interview

- Ask **2–4 questions per turn**, never a wall of questions. Use AskUserQuestion when
  there are natural options (languages, seniority, target roles); open questions otherwise.
- After each section, play back a 2–3 line summary so they can correct it.
- Dig for results: when they describe a duty, ask one follow-up to find the impact
  ("¿Qué cambió gracias a eso? ¿Hay algún número: usuarios, tiempo, %, tamaño del equipo?").
  If there's no number, keep the bullet qualitative. **Never estimate numbers for them.**
- Use their words for facts; you only improve the phrasing.
- Save progress as you go to `me/cv_interview_notes.md` (raw facts per section), so an
  interrupted session can resume. If that file exists when you start, resume from it.

## Order

1. **Goal:** target role(s), seniority, markets, CV languages needed (EN, ES, both).
2. **Contact:** name, city/country, email, phone, LinkedIn, GitHub/portfolio (optional).
3. **Experience** (most recent first). For each role: company, what the company does (one
   line), title, location and modality, start/end month-year, 3–6 things they did with
   results, technologies used. Ask whether older or unrelated roles are worth including.
4. **Projects** (personal, freelance, open source), especially if experience is short.
5. **Education, certifications and courses** (name, institution, dates).
6. **Languages** and honest level.
7. **Skills:** confirm the consolidated list you inferred from the roles; ask what's missing.

## Write, review, render

Write the summary last (it's easier once you know everything). Then follow steps 4–6 of
the `cv-review` skill: write `me/cv_<lang>.md` per the template, check every sentence
against the notes, review the changes with the user, and render with
`python3 tools/render_cv.py`. Keep `me/cv_interview_notes.md` as the factual record.
