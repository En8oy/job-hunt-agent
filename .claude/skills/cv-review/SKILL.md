---
name: cv-review
description: Read the user's existing CV (PDF, DOCX, Markdown or text in me/cv_original/), convert it to Markdown and rewrite it to ATS standards in English and/or Spanish, asking the user to fill gaps instead of inventing, then render the PDFs. Use for /cv-review, "revisa mi CV", "improve my resume", or when /setup finds a CV.
---

# /cv-review

Turn the user's current CV into `me/cv_en.md` and/or `me/cv_es.md` that pass applicant
tracking systems (ATS) and read well to a human, **without adding anything that isn't
true**. Talk in the user's language.

Read `references/ats-guidelines.md` and `references/cv-template.md` before writing.

## 1. Read the source

- Find the input in `me/cv_original/` (if several files, ask which one is current).
  - PDF → Read tool (use `pages` for long files).
  - DOCX → `unzip -p <file> word/document.xml | sed -e 's/<\/w:p>/\n/g; s/<[^>]*>//g'`.
  - `.md` / `.txt` → read directly.
  - A LinkedIn "Save to PDF" export works too.
- If `me/cv_*.md` already exist, this is a re-review: start from those instead and use
  the original only for anything missing.
- Never modify files in `me/cv_original/`.

## 2. Extract the facts

Build a faithful inventory: contact info, roles (company, title, location, modality,
dates), responsibilities, achievements with any numbers, stack per role, projects,
education, certifications/courses, languages and level. Keep the user's own numbers and
claims exactly as stated.

## 3. Diagnose, then ask

Show a short diagnosis (5–10 bullets max): what blocks ATS parsing (tables, columns,
images, headers/footers, icons for contact info, non-standard section names, missing dates),
weak bullets (duties without results), missing keywords for the roles they target,
length, and inconsistencies (overlapping dates, unexplained gaps).

Then ask **only what you need** to strengthen it, in small batches (2–4 questions per
turn, use AskUserQuestion when there are clear options):
- Which languages do they need? (Default: both EN and ES if they target Latin America
  plus remote/US; otherwise just the local one.)
- What roles are they targeting? (Shapes the headline and keyword emphasis.)
- For the 3–5 most important bullets: is there a real number behind it (users, %, time
  saved, team size, revenue, performance)? If they don't know one, keep the bullet
  qualitative — **never estimate a number for them**.
- Missing essentials: month/year for dates, location/modality, gaps they want explained.

## 4. Write

Write `me/cv_<lang>.md` following `references/cv-template.md` exactly (the PDF renderer
depends on that structure). For a second language, translate naturally (not word for
word), keep job titles and technologies in their common form for that market, and keep
both versions factually identical.

Before saving, check every sentence against the inventory from step 2 and the user's
answers. If something isn't backed by either, remove it.

## 5. Review with the user

Show a compact summary of what changed and why (not the whole CV), and point them to the
file. Ask for approval or changes; iterate until they approve.

## 6. Render

`python3 tools/render_cv.py me/cv_en.md me/cv_es.md` (only the languages that exist; add
`--paper letter` if they mostly target the US). Read the first page of each PDF to
check nothing broke, and tell the user where the files are. Remind them to replace the
CV stored on each job platform; those copies don't update by themselves.
