#!/usr/bin/env python3
"""Job search tracker CLI over SQLite. All output is JSON so agents can parse it.

Your data lives in the private me/ folder: DB at me/data/job_search.db ($JOB_SEARCH_DB
overrides it), and after every write a consistent copy is saved to
me/data/backup/job_search.db.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = HERE / "schema.sql"
ROOT = HERE.parent
DB_PATH = Path(os.environ.get("JOB_SEARCH_DB", ROOT / "me" / "data" / "job_search.db"))
BACKUP = DB_PATH.parent / "backup" / DB_PATH.name

APP_STATUSES = ['applied', 'in_review', 'screening', 'needs_info', 'in_process',
                'offer', 'hired', 'rejected', 'withdrawn', 'no_response', 'on_hold']
STEP_TYPES = ['questionnaire', 'recruiter_screen', 'english', 'cognitive', 'psychometric',
              'coding_test', 'take_home', 'technical', 'system_design', 'video_intro',
              'hiring_manager', 'team_meet', 'founder_ceo', 'client', 'culture_fit',
              'salary_negotiation', 'background_check', 'references', 'paid_trial',
              'offer', 'other']
STEP_STATUSES = ['planned', 'to_schedule', 'scheduled', 'done', 'passed', 'failed', 'skipped', 'cancelled']
EVENT_TYPES = ['applied', 'email', 'message', 'status_change', 'assessment',
               'interview', 'rejection', 'offer', 'duplicate', 'note']

LEGAL_SUFFIXES = r"\b(s\.?\s?a\.?\s?p\.?\s?i\.?|s\.?\s?a\.?|de|c\.?\s?v\.?|s\.?\s?de\s?r\.?\s?l\.?|llc|inc|ltd|limited|corp|sc|gmbh|careers)\b"
ANONYMOUS = re.compile(r"confidencial|importante empresa|cliente no|no revelado|no identificado|^none$|^\(", re.I)


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm_company(name):
    s = strip_accents(name or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)              # drop "(via X)", "(cliente ...)"
    s = re.sub(LEGAL_SUFFIXES, " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def norm_position(title):
    s = strip_accents(title or "").lower()
    s = re.sub(r"[^a-z0-9+#]+", " ", s)
    return " ".join(s.split())


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='applications'").fetchone():
        conn.executescript(SCHEMA.read_text())   # first use creates the tables
    return conn


def backup(conn):
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    tmp = BACKUP.with_suffix(".db.tmp")
    dst = sqlite3.connect(tmp)
    conn.backup(dst)
    dst.close()
    os.replace(tmp, BACKUP)                      # atomic, so Seafile never sees a partial file


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1, default=str))


def rows(cur):
    return [dict(r) for r in cur.fetchall()]


def get_or_create_company(conn, name):
    norm = norm_company(name)
    if not norm or ANONYMOUS.search(name.strip()):
        # Anonymous employers are never the same company as each other.
        norm = f"anon:{norm or 'unknown'}:{datetime.now().timestamp()}"
    row = conn.execute("SELECT id FROM companies WHERE name_norm=?", (norm,)).fetchone()
    if row:
        return row["id"]
    return conn.execute("INSERT INTO companies(name, name_norm) VALUES (?,?)", (name.strip(), norm)).lastrowid


def get_or_create_contact(conn, email, name=None, company_id=None, role=None):
    if not email:
        return None
    row = conn.execute("SELECT id FROM contacts WHERE email=?", (email.lower(),)).fetchone()
    if row:
        return row["id"]
    return conn.execute("INSERT INTO contacts(email, name, company_id, role) VALUES (?,?,?,?)",
                        (email.lower(), name, company_id, role)).lastrowid


def find_matches(conn, url=None, company=None, position=None):
    """Existing applications/candidates that look like the same job."""
    res = {"applications": [], "candidates": [], "same_company_recent": []}
    if url:
        res["applications"] += rows(conn.execute(
            "SELECT a.id, c.name company, a.position, a.platform, a.status, a.applied_at FROM applications a "
            "JOIN companies c ON c.id=a.company_id WHERE a.job_url=?", (url,)))
        res["candidates"] += rows(conn.execute("SELECT * FROM candidates WHERE job_url=?", (url,)))
    if company:
        cn = norm_company(company)
        if position:
            res["applications"] += rows(conn.execute(
                "SELECT a.id, c.name company, a.position, a.platform, a.status, a.applied_at FROM applications a "
                "JOIN companies c ON c.id=a.company_id WHERE c.name_norm=? AND a.position_norm=?",
                (cn, norm_position(position))))
        res["same_company_recent"] = rows(conn.execute(
            "SELECT a.id, a.position, a.platform, a.status, a.applied_at FROM applications a "
            "JOIN companies c ON c.id=a.company_id WHERE c.name_norm=? "
            "AND (a.applied_at IS NULL OR a.applied_at >= date('now','-30 days'))", (cn,)))
    seen = set()
    res["applications"] = [a for a in res["applications"] if not (a["id"] in seen or seen.add(a["id"]))]
    res["exists"] = bool(res["applications"] or res["candidates"])
    return res


def add_event(conn, app_id, type_, summary, quote=None, occurred_at=None, source=None,
              contact_id=None, from_status=None, to_status=None):
    return conn.execute(
        "INSERT INTO events(application_id, occurred_at, type, source, contact_id, summary, quote, from_status, to_status) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (app_id, occurred_at, type_, source, contact_id, summary, quote, from_status, to_status)).lastrowid


def touch(conn, app_id):
    conn.execute("UPDATE applications SET updated_at=? WHERE id=?", (now(), app_id))


def app_detail(conn, app_id):
    app = conn.execute(
        "SELECT a.*, c.name company FROM applications a JOIN companies c ON c.id=a.company_id WHERE a.id=?",
        (app_id,)).fetchone()
    if not app:
        return None
    d = dict(app)
    d["steps"] = rows(conn.execute("SELECT * FROM steps WHERE application_id=? ORDER BY seq", (app_id,)))
    d["tasks"] = rows(conn.execute("SELECT * FROM tasks WHERE application_id=? ORDER BY status, due_at", (app_id,)))
    d["events"] = rows(conn.execute(
        "SELECT * FROM events WHERE application_id=? ORDER BY COALESCE(occurred_at, recorded_at)", (app_id,)))
    d["screening_answers"] = rows(conn.execute("SELECT * FROM screening_answers WHERE application_id=?", (app_id,)))
    return d


# ---------------------------------------------------------------- commands

def cmd_init(conn, a):
    conn.executescript(SCHEMA.read_text())
    return {"db": str(DB_PATH)}


def cmd_exists(conn, a):
    return find_matches(conn, a.url, a.company, a.position)


def cmd_add_app(conn, a):
    m = find_matches(conn, a.url, a.company, a.position)
    if m["applications"] and not a.force:
        return {"error": "duplicate", "matches": m["applications"],
                "hint": "log the extra platform with `event APP_ID --type duplicate` instead"}
    cid = get_or_create_company(conn, a.company)
    app_id = conn.execute(
        "INSERT INTO applications(company_id, position, position_norm, platform, ats, job_url, status, applied_at, "
        "modality, location, seniority, salary_text, cv_used, fit_notes, honesty_flags, applied_by) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (cid, a.position, norm_position(a.position), a.platform, a.ats, a.url, a.status,
         a.applied_at or datetime.now().strftime("%Y-%m-%d"), a.modality, a.location, a.seniority,
         a.salary, a.cv, a.fit_notes, a.honesty, a.by)).lastrowid
    add_event(conn, app_id, "applied", f"Applied via {a.platform}" + (f" -> {a.ats}" if a.ats else ""),
              occurred_at=a.applied_at or now(), source=a.by)
    conn.execute("UPDATE candidates SET decision='applied', application_id=? WHERE job_url=? AND ?<>''",
                 (app_id, a.url, a.url or ""))
    return {"id": app_id}


def cmd_status(conn, a):
    app = conn.execute("SELECT status FROM applications WHERE id=?", (a.app_id,)).fetchone()
    if not app:
        return {"error": f"application {a.app_id} not found"}
    if a.status == "rejected" and not a.quote:
        return {"error": "rejections require --quote with the literal rejection sentence"}
    conn.execute("UPDATE applications SET status=?, updated_at=? WHERE id=?", (a.status, now(), a.app_id))
    cont = get_or_create_contact(conn, a.contact_email, a.contact_name)
    ev_type = "rejection" if a.status == "rejected" else "offer" if a.status == "offer" else "status_change"
    eid = add_event(conn, a.app_id, ev_type, a.summary, a.quote, a.occurred_at, a.source, cont,
                    app["status"], a.status)
    return {"id": a.app_id, "from": app["status"], "to": a.status, "event_id": eid}


def cmd_event(conn, a):
    cont = get_or_create_contact(conn, a.contact_email, a.contact_name)
    eid = add_event(conn, a.app_id, a.type, a.summary, a.quote, a.occurred_at, a.source, cont)
    touch(conn, a.app_id)
    return {"event_id": eid}


STEP_FIELDS = ["name", "type", "status", "modality", "scheduled_at", "duration_min",
               "deadline_at", "link", "result", "details"]


def cmd_step_add(conn, a):
    if a.details:
        json.loads(a.details)
    seq = a.seq or (conn.execute("SELECT COALESCE(MAX(seq),0)+1 FROM steps WHERE application_id=?",
                                 (a.app_id,)).fetchone()[0])
    sid = conn.execute(
        "INSERT INTO steps(application_id, seq, name, type, status, modality, scheduled_at, duration_min, "
        "deadline_at, link, result, details, defined_by, source_event_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (a.app_id, seq, a.name, a.type, a.status, a.modality, a.scheduled_at, a.duration_min,
         a.deadline_at, a.link, a.result, a.details, a.by, a.event_id)).lastrowid
    touch(conn, a.app_id)
    return {"step_id": sid, "seq": seq}


def cmd_step_update(conn, a):
    sets = {f: getattr(a, f) for f in STEP_FIELDS if getattr(a, f) is not None}
    if "details" in sets:
        json.loads(sets["details"])
    if not sets:
        return {"error": "nothing to update"}
    sets["updated_at"] = now()
    conn.execute(f"UPDATE steps SET {', '.join(k + '=?' for k in sets)} WHERE id=?", (*sets.values(), a.step_id))
    row = conn.execute("SELECT * FROM steps WHERE id=?", (a.step_id,)).fetchone()
    touch(conn, row["application_id"])
    return dict(row)


def cmd_task_add(conn, a):
    app_id = a.app_id
    if a.step_id and not app_id:
        app_id = conn.execute("SELECT application_id FROM steps WHERE id=?", (a.step_id,)).fetchone()[0]
    tid = conn.execute("INSERT INTO tasks(application_id, step_id, owner, title, due_at, link) VALUES (?,?,?,?,?,?)",
                       (app_id, a.step_id, a.owner, a.title, a.due_at, a.link)).lastrowid
    return {"task_id": tid}


def cmd_task_done(conn, a):
    conn.execute("UPDATE tasks SET status=?, done_at=? WHERE id=?", (a.status, now(), a.task_id))
    return dict(conn.execute("SELECT * FROM tasks WHERE id=?", (a.task_id,)).fetchone())


def cmd_answer_add(conn, a):
    aid = conn.execute(
        "INSERT INTO screening_answers(application_id, step_id, question, answer, topic, honesty_note, answered_by) "
        "VALUES (?,?,?,?,?,?,?)",
        (a.app_id, a.step_id, a.question, a.answer, a.topic, a.honesty, a.by)).lastrowid
    return {"answer_id": aid}


def cmd_answers(conn, a):
    q = "SELECT s.*, c.name company, ap.position FROM screening_answers s JOIN applications ap ON ap.id=s.application_id " \
        "JOIN companies c ON c.id=ap.company_id"
    args = ()
    if a.topic:
        q += " WHERE s.topic=?"
        args = (a.topic,)
    return rows(conn.execute(q + " ORDER BY s.answered_at DESC LIMIT 50", args))


def cmd_cand_add(conn, a):
    m = find_matches(conn, a.url, a.company, a.position)
    if m["exists"]:
        return {"skipped": "already tracked", "matches": m}
    cid = conn.execute(
        "INSERT INTO candidates(platform, job_url, company, position, fit_score, fit_notes, decision, skip_reason) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (a.platform, a.url, a.company, a.position, a.fit, a.notes, a.decision, a.skip_reason)).lastrowid
    return {"candidate_id": cid, "same_company_recent": m["same_company_recent"]}


def cmd_cand_claim(conn, a):
    """Atomically claim the next candidate marked 'apply' so parallel agents never collide."""
    conn.execute("BEGIN IMMEDIATE")
    q = "SELECT id FROM candidates WHERE decision='apply' AND claimed_by IS NULL"
    args = []
    if a.platform:
        q += " AND platform=?"
        args.append(a.platform)
    row = conn.execute(q + " ORDER BY fit_score DESC, found_at LIMIT 1", args).fetchone()
    if not row:
        conn.execute("COMMIT")
        return {"candidate": None}
    conn.execute("UPDATE candidates SET claimed_by=?, claimed_at=? WHERE id=?", (a.agent, now(), row["id"]))
    conn.execute("COMMIT")
    return {"candidate": dict(conn.execute("SELECT * FROM candidates WHERE id=?", (row["id"],)).fetchone())}


def cmd_cand_set(conn, a):
    conn.execute("UPDATE candidates SET decision=COALESCE(?,decision), skip_reason=COALESCE(?,skip_reason), "
                 "application_id=COALESCE(?,application_id) WHERE id=?",
                 (a.decision, a.skip_reason, a.app_id, a.cand_id))
    return dict(conn.execute("SELECT * FROM candidates WHERE id=?", (a.cand_id,)).fetchone())


def cmd_cands(conn, a):
    q = "SELECT * FROM candidates WHERE 1=1"
    args = []
    if a.decision:
        q += " AND decision=?"
        args.append(a.decision)
    if a.platform:
        q += " AND platform=?"
        args.append(a.platform)
    return rows(conn.execute(q + " ORDER BY found_at DESC LIMIT 100", args))


def cmd_run_start(conn, a):
    return {"run_id": conn.execute("INSERT INTO runs(kind, platform) VALUES (?,?)", (a.kind, a.platform)).lastrowid}


def cmd_run_finish(conn, a):
    conn.execute("UPDATE runs SET finished_at=?, summary=? WHERE id=?", (now(), a.summary, a.run_id))
    return {"run_id": a.run_id}


def cmd_last_run(conn, a):
    row = conn.execute("SELECT * FROM runs WHERE kind=? AND finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1",
                       (a.kind,)).fetchone()
    return dict(row) if row else {"run": None}


def cmd_show(conn, a):
    return app_detail(conn, a.app_id) or {"error": f"application {a.app_id} not found"}


def cmd_find(conn, a):
    like = f"%{norm_position(a.text)}%"
    return rows(conn.execute(
        "SELECT a.id, c.name company, a.position, a.platform, a.status, a.applied_at FROM applications a "
        "JOIN companies c ON c.id=a.company_id WHERE c.name_norm LIKE ? OR a.position_norm LIKE ? "
        "ORDER BY a.applied_at DESC", (f"%{norm_company(a.text)}%", like)))


def cmd_pending(conn, a):
    return {
        "tasks": rows(conn.execute(
            "SELECT t.*, c.name company, ap.position FROM tasks t LEFT JOIN applications ap ON ap.id=t.application_id "
            "LEFT JOIN companies c ON c.id=ap.company_id WHERE t.status='open' ORDER BY t.due_at IS NULL, t.due_at")),
        "upcoming_steps": rows(conn.execute(
            "SELECT s.*, c.name company, ap.position FROM steps s JOIN applications ap ON ap.id=s.application_id "
            "JOIN companies c ON c.id=ap.company_id WHERE s.status IN ('scheduled','to_schedule') "
            "ORDER BY s.scheduled_at IS NULL, s.scheduled_at")),
        "needs_info": rows(conn.execute(
            "SELECT a.id, c.name company, a.position, a.platform FROM applications a "
            "JOIN companies c ON c.id=a.company_id WHERE a.status='needs_info'")),
    }


def cmd_backup(conn, a):
    backup(conn)
    return {"backup": str(BACKUP)}


# ---------------------------------------------------------------- argparse

def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    def sub(name, fn, write, help_):
        s = sp.add_parser(name, help=help_)
        s.set_defaults(fn=fn, write=write)
        return s

    sub("init", cmd_init, True, "create tables")

    s = sub("exists", cmd_exists, False, "check if a job is already tracked (by URL and/or company+position)")
    s.add_argument("--url"); s.add_argument("--company"); s.add_argument("--position")

    s = sub("add-app", cmd_add_app, True, "log a submitted application")
    s.add_argument("--company", required=True); s.add_argument("--position", required=True)
    s.add_argument("--platform", required=True); s.add_argument("--ats"); s.add_argument("--url")
    s.add_argument("--status", default="applied", choices=APP_STATUSES)
    s.add_argument("--applied-at"); s.add_argument("--modality", choices=["remote", "hybrid", "onsite"])
    s.add_argument("--location"); s.add_argument("--seniority", choices=["junior", "mid", "senior", "lead"])
    s.add_argument("--salary"); s.add_argument("--cv", choices=["en", "es"])
    s.add_argument("--fit-notes"); s.add_argument("--honesty")
    s.add_argument("--by", default="agent", choices=["agent", "user"])
    s.add_argument("--force", action="store_true", help="insert even if a duplicate is found")

    s = sub("status", cmd_status, True, "change an application's status (logs an event)")
    s.add_argument("app_id", type=int); s.add_argument("status", choices=APP_STATUSES)
    s.add_argument("--summary", required=True); s.add_argument("--quote"); s.add_argument("--occurred-at")
    s.add_argument("--source", default="email"); s.add_argument("--contact-email"); s.add_argument("--contact-name")

    s = sub("event", cmd_event, True, "add an event to an application's history")
    s.add_argument("app_id", type=int); s.add_argument("--type", required=True, choices=EVENT_TYPES)
    s.add_argument("--summary", required=True); s.add_argument("--quote"); s.add_argument("--occurred-at")
    s.add_argument("--source"); s.add_argument("--contact-email"); s.add_argument("--contact-name")

    def step_args(s, required):
        s.add_argument("--name", required=required)
        s.add_argument("--type", required=required, choices=STEP_TYPES)
        s.add_argument("--status", choices=STEP_STATUSES, default="planned" if required else None)
        s.add_argument("--modality", choices=["remote", "onsite", "async"])
        s.add_argument("--scheduled-at"); s.add_argument("--duration-min", type=int)
        s.add_argument("--deadline-at"); s.add_argument("--link"); s.add_argument("--result")
        s.add_argument("--details", help="JSON object")

    s = sub("step-add", cmd_step_add, True, "add a hiring-process step")
    s.add_argument("app_id", type=int); step_args(s, True); s.add_argument("--seq", type=int)
    s.add_argument("--by", default="ai", choices=["ai", "user", "company"]); s.add_argument("--event-id", type=int)

    s = sub("step-update", cmd_step_update, True, "update a step")
    s.add_argument("step_id", type=int); step_args(s, False)

    s = sub("task-add", cmd_task_add, True, "add a to-do")
    s.add_argument("--app-id", type=int); s.add_argument("--step-id", type=int)
    s.add_argument("--title", required=True); s.add_argument("--due-at"); s.add_argument("--link")
    s.add_argument("--owner", default="user", choices=["user", "agent"])

    s = sub("task-done", cmd_task_done, True, "close a to-do")
    s.add_argument("task_id", type=int)
    s.add_argument("--status", default="done", choices=["done", "expired", "cancelled"])

    s = sub("answer-add", cmd_answer_add, True, "record a screening question and the answer given")
    s.add_argument("app_id", type=int); s.add_argument("--question", required=True)
    s.add_argument("--answer", required=True); s.add_argument("--topic"); s.add_argument("--honesty")
    s.add_argument("--step-id", type=int); s.add_argument("--by", default="agent", choices=["agent", "user"])

    s = sub("answers", cmd_answers, False, "list past screening answers (keep them consistent)")
    s.add_argument("--topic")

    s = sub("cand-add", cmd_cand_add, True, "record a job found by a search agent")
    s.add_argument("--platform", required=True); s.add_argument("--company", required=True)
    s.add_argument("--position", required=True); s.add_argument("--url")
    s.add_argument("--fit", type=int); s.add_argument("--notes")
    s.add_argument("--decision", default="pending", choices=["pending", "apply", "skip"])
    s.add_argument("--skip-reason")

    s = sub("cand-claim", cmd_cand_claim, True, "atomically take the next candidate to apply to")
    s.add_argument("--agent", required=True); s.add_argument("--platform")

    s = sub("cand-set", cmd_cand_set, True, "update a candidate's decision")
    s.add_argument("cand_id", type=int)
    s.add_argument("--decision", choices=["pending", "apply", "skip", "applied"])
    s.add_argument("--skip-reason"); s.add_argument("--app-id", type=int)

    s = sub("cands", cmd_cands, False, "list candidates")
    s.add_argument("--decision"); s.add_argument("--platform")

    s = sub("run-start", cmd_run_start, True, "start a run log")
    s.add_argument("kind", choices=["email_check", "search", "apply", "keyword_sweep", "migration"])
    s.add_argument("--platform")
    s = sub("run-finish", cmd_run_finish, True, "finish a run log")
    s.add_argument("run_id", type=int); s.add_argument("--summary", required=True)
    s = sub("last-run", cmd_last_run, False, "most recent finished run of a kind")
    s.add_argument("kind")

    s = sub("show", cmd_show, False, "full detail of one application")
    s.add_argument("app_id", type=int)
    s = sub("find", cmd_find, False, "search applications by company or position text")
    s.add_argument("text")
    sub("pending", cmd_pending, False, "open tasks, upcoming steps, needs_info applications")
    sub("backup", cmd_backup, False, "copy the DB to the Curriculum backup folder")
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    conn = connect()
    try:
        with conn:
            result = a.fn(conn, a)
        if a.write and not (isinstance(result, dict) and "error" in result):
            backup(conn)
    except (sqlite3.IntegrityError, json.JSONDecodeError) as e:
        result = {"error": str(e)}
    out(result)
    return 1 if isinstance(result, dict) and "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
