# me/ — your private folder

Everything in here is ignored by git (see `.gitignore`), so it is never committed or pushed.

| File | Created by |
|---|---|
| `cv_original/` | You. Drop your current CV here (PDF, DOCX, Markdown or plain text). Never modified. |
| `cv_en.md`, `cv_es.md` | `/cv-review` or `/cv-interview`. Your ATS-ready CV, the source of truth. |
| `cv_en.pdf`, `cv_es.pdf` | Generated from the `.md` files with `python3 tools/render_cv.py`. |
| `profile.yml` | `/setup` or `/profile`. Search titles, salary, modality, platforms, rules. |
| `data/job_search.db` | The tracker database (`tracker/tracker.py`). Backup in `data/backup/`. |
