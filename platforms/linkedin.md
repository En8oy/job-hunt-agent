# LinkedIn

Status: active — last verified 2026-10-18
URL: https://www.linkedin.com/jobs/
Account: required (the user must be signed in). Stores CVs under Settings → Job application settings → Resumes.
Type: job board + feed

## Search
- Jobs tab: search each title, filter "Remote" (and the user's on-site cities if allowed), "Date posted: past week".
- **Also search posts, not just Jobs**: many recruiters only post in the feed. Use the main search with the
  "Posts" filter for phrases like "hiring full stack", "estamos contratando", "buscamos desarrollador" plus the
  user's core technologies. Posts are noisy (often "DM me" or "link in comments"); judge fit from what's there,
  and follow external links to the company's form or career site.
- Many good matches route to an external ATS (Greenhouse, Lever, Ashby, Workday, Workable): record
  `--platform linkedin --ats <name>`.

## Apply
- Easy Apply: multi-step modal, preloaded answers. Check every prefilled number (years of experience, salary);
  LinkedIn reuses stale values.
- Resume picker: choose the CV in the posting's language. Check the file size shown next to it; a stored CV has
  shown as a broken 0-byte file before. If so, upload the right PDF from `me/` or fall back to the other
  language and flag it so the user can re-upload it in their settings.
- "Apply" (external) opens the company site: apply there like any other site, never create accounts.

## Known issues
- 2026-10-01: a stored Spanish CV appeared as 0 bytes ("Please select a smaller file") in Easy Apply.
