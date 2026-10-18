---
name: check-email
description: Check the user's inbox for recruiter replies, rejections, interview invites and assessments, and log them to the tracker (status, events, hiring steps, to-dos). Use for /check-email, "revisa mi correo", "any replies?".
---

# /check-email

1. Preconditions: `me/profile.yml` with `disclaimer_accepted_at` set and `person.email` /
   `person.email_webmail` filled; Claude in Chrome responding (`tabs_context_mcp`). If
   something is missing, say what and stop.
2. Launch one `email-checker` agent with the Agent tool
   (`subagent_type: "email-checker"`) and wait for it.
3. Relay its report to the user in their language, most urgent first:
   - **Needs your action** (with dates): interviews to accept, tests with deadlines,
     documents to upload, questions to answer.
   - **News:** rejections (with the quoted sentence), advances, new steps.
   - **Backfilled:** applications found in email that weren't tracked.
   - Nothing new → say so plainly.
