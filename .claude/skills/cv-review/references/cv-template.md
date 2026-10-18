# CV Markdown template

`tools/render_cv.py` relies on this structure. Keep it exactly: a `#` name, a `###`
headline right after it, plain contact lines, `---` before each section, `##` sections,
`###` entries.

```markdown
# Full Name
### Target Role · One differentiator

City, Region, Country · Open to remote work

email@example.com · +52 000 000 0000
linkedin.com/in/handle · github.com/handle · portfolio.dev

---

## Profile

Three or four lines: years of experience, core stack, domain, one standout result.

---

## Professional Experience

### Company · Job Title
City, Country *(remote)* — Mon YYYY – Mon YYYY

One line of context about the company if it isn't well known.

- Action verb + what + how + result (with a number when real).
- ...

**Stack:** Tech, Tech, Tech

### Previous Company · Job Title
...

---

## Projects

### Project name · short description (status)

- ...

**Stack:** ...

---

## Education

**Degree name** · Mon YYYY – Mon YYYY
Institution, City

**Relevant courses:** Course (YYYY) · Course (YYYY)

---

## Skills

**Languages & frameworks:** ...
**Data & infrastructure:** ...
**Tools:** ...

---

## Languages

**Spanish:** Native · **English:** Professional working proficiency (B2)
```

Notes:
- Contact lines between the headline and the first `---` keep their line breaks; separate
  them with blank lines or put each on its own line.
- Use `·` (middle dot) as the separator, ` — ` before dates, ` – ` between dates.
- Spanish files use the Spanish section names from `ats-guidelines.md`.
