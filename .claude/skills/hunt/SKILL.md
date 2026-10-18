---
name: hunt
description: Run a job-hunting pass — search the enabled platforms in parallel with platform-search agents, then apply one by one with the applier agent, asking the user any opinion questions in chat. Use for /hunt, "/hunt linkedin occ", "busca trabajo", "apply to jobs".
---

# /hunt [platform ...]

Orchestrate one hunting pass. You coordinate; the agents do the browsing.

## 0. Preconditions

- `me/profile.yml` must exist with `disclaimer_accepted_at` set. If not, stop and tell the
  user to run `/setup`.
- `me/cv_*.pdf` must exist. If not, suggest `/cv-review`.
- Claude in Chrome must respond: load it with ToolSearch
  (`select:mcp__claude-in-chrome__tabs_context_mcp`) and call `tabs_context_mcp`. If it
  fails, stop and explain how to connect the extension.

## 1. Pick platforms

Use the platforms named in the arguments, otherwise every platform with `enabled: true`
in `me/profile.yml`. For each, read the `Status` line at the top of `platforms/<name>.md`:
skip it when the status says it requires an account and the profile says
`account: false`, or when it's marked broken. Tell the user which platforms will run and
which are skipped and why.

## 2. Search in parallel

Launch one `platform-search` agent per platform with the Agent tool
(`subagent_type: "platform-search"`), **at most 3 at a time** so the browser isn't
overloaded. Prompt for each: `Platform: <name>`. They only search and record candidates;
they never apply. Wait for each to finish (you'll be notified). Relay a one-line progress
update to the user as each finishes.

## 3. Apply one at a time

Run `python3 tracker/tracker.py cands --decision apply` to see the queue. If it's empty,
skip to the summary. Otherwise launch **one** `applier` agent (never two in parallel —
they share the user's browser and accounts). It processes the queue until empty or until
`rules.batch_per_platform` is reached for each platform.

The applier can't talk to the user. When an application needs an answer only the user can
give (opinion questions, a fact missing from the CV/profile), it leaves that candidate
unsubmitted and returns the question. After it finishes:
- Ask those questions in chat, grouped per job (AskUserQuestion or plain questions).
- Save reusable facts the user gives you into `me/profile.yml` (e.g. notice period).
- Relaunch the applier with the answers in its prompt, for just those candidate ids.

## 4. Summary

Give the user a short summary: per platform, jobs found / applied / skipped; anything
marked `needs_info` with what's missing; platform problems (login walls, CAPTCHAs, broken
filters) and which `platforms/*.md` notes were updated. Suggest `/dashboard` to review.
