#!/usr/bin/env python3
"""Local dashboard for the job search tracker: python3 tracker/dashboard.py [--port 8765]

Serves on 127.0.0.1 only. Read-only except for closing tasks (button on each to-do).
Every table is paginated server-side; the query string keeps each table's page and filters.
"""
import argparse
import html
import json
import math
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import tracker as t

PROFILE = t.ROOT / "me" / "profile.yml"

STATUS_LABEL = {
    "applied": "Aplicada", "in_review": "En revisión", "screening": "Screening", "needs_info": "Falta info",
    "in_process": "En proceso", "offer": "Oferta", "hired": "Contratado", "rejected": "Rechazada",
    "withdrawn": "Retirada", "no_response": "Sin respuesta", "on_hold": "En pausa",
}
STEP_LABEL = {
    "questionnaire": "Cuestionario", "recruiter_screen": "Entrevista inicial", "english": "Inglés",
    "cognitive": "Cognitiva", "psychometric": "Psicométrica", "coding_test": "Prueba de código",
    "take_home": "Take-home", "technical": "Técnica", "system_design": "System design",
    "video_intro": "Video intro", "hiring_manager": "Hiring manager", "team_meet": "Equipo",
    "founder_ceo": "CEO / fundador", "client": "Cliente", "culture_fit": "Culture fit",
    "salary_negotiation": "Salario", "background_check": "Estudio socioeconómico", "references": "Referencias",
    "paid_trial": "Prueba pagada", "offer": "Oferta", "other": "Otro",
}
ACTIVE = ("screening", "needs_info", "in_process", "offer")
RESPONDED = ("in_review", "screening", "in_process", "offer", "hired", "rejected")
# An application "advanced" if it reached a real hiring stage, even if it was rejected later.
ADVANCED_SQL = ("(a.status IN ('screening','in_process','offer','hired') OR EXISTS (SELECT 1 FROM steps s "
                "WHERE s.application_id=a.id AND s.status NOT IN ('planned','cancelled','skipped')))")
MVP_MIN_APPS = 10


def wilson_low(hits, n, z=1.96):
    """Lower bound of the 95% Wilson interval: a small sample can't win on luck (2 of 5 ≠ 40%)."""
    if not n:
        return 0.0
    p = hits / n
    return max(0.0, (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n))

CSS = """
:root{--bg:#f6f5f2;--card:#fff;--fg:#1d1d1b;--muted:#6b6a65;--line:#e4e2dc;--accent:#2f5bd3;
--ok:#1f7a4d;--warn:#b26a00;--bad:#b3261e;--chip:#efeee9;--hl:#eef3ff}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1f1f1d;--fg:#ecebe6;--muted:#9c9a92;
--line:#33322e;--accent:#7f9cff;--ok:#5cc28f;--warn:#e0a640;--bad:#ff7b72;--chip:#2a2a27;--hl:#1e2433}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:15px;text-transform:uppercase;letter-spacing:.06em;
color:var(--muted);margin:32px 0 10px}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.sub{color:var(--muted);font-size:13px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:18px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi b{display:block;font-size:26px;font-variant-numeric:tabular-nums}.kpi span{color:var(--muted);font-size:13px}
.mvp{background:var(--hl);border:1px solid var(--accent);border-radius:10px;padding:14px 16px;margin-top:12px}
.mvp b{font-size:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);
vertical-align:top}th{font-size:12px;color:var(--muted);font-weight:600}tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.chip{display:inline-block;padding:1px 8px;border-radius:99px;background:var(--chip);font-size:12px;white-space:nowrap;margin:1px 2px 1px 0}
.s-passed{color:var(--ok)}.s-failed{color:var(--bad)}.s-scheduled,.s-to_schedule{color:var(--warn);font-weight:600}
.overdue{color:var(--bad);font-weight:600}.soon{color:var(--warn);font-weight:600}
.empty{padding:14px;color:var(--muted)}
button,select,input{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--card);color:var(--fg);
border-radius:6px;padding:4px 8px}button{background:var(--chip);cursor:pointer}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}.filters input[type=search]{flex:1;min-width:200px}
.pager{display:flex;gap:6px;align-items:center;justify-content:flex-end;padding:8px 12px;border-top:1px solid var(--line);
font-size:13px;color:var(--muted)}.pager a,.pager span.cur{padding:2px 8px;border-radius:6px;border:1px solid var(--line)}
.pager span.cur{background:var(--accent);color:#fff;border-color:var(--accent)}
.bar{height:8px;background:var(--accent);border-radius:4px;min-width:2px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:800px){.grid2{grid-template-columns:1fr}}
.wrap{overflow-x:auto}.ev{font-size:13px}.when{color:var(--muted);white-space:nowrap}
pre{white-space:pre-wrap;margin:0;font:inherit}
"""


def e(v):
    return html.escape("" if v is None else str(v))


def due_class(when):
    if not when:
        return ""
    if when < datetime.now().strftime("%Y-%m-%d %H:%M"):
        return "overdue"
    return "soon" if when[:10] <= datetime.now().strftime("%Y-%m-%d") else ""


def link(url, text=None):
    m = re.search(r"https?://\S+", url or "")
    if not m:
        return e(url)
    return f'<a href="{e(m.group(0).rstrip(").,"))}" target="_blank" rel="noopener">{e(text or url)}</a>'


def person_name():
    try:
        m = re.search(r"^\s+name:\s*['\"]?([^'\"\n#]+)", PROFILE.read_text(), re.M)
        return m.group(1).strip() if m else None
    except OSError:
        return None


def page(title, body):
    return (f"<!doctype html><html lang=es><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{e(title)}</title><style>{CSS}</style><main>{body}</main></html>")


class Pager:
    """Server-side pagination for one table; `key` namespaces its page param in the query string."""

    def __init__(self, conn, params, key, sql, args=(), per_page=15):
        self.params, self.key, self.per = params, key, per_page
        self.total = conn.execute(f"SELECT COUNT(*) FROM ({sql})", args).fetchone()[0]
        self.pages = max(1, -(-self.total // per_page))
        try:
            self.page = min(max(1, int(params.get(key, ["1"])[0])), self.pages)
        except ValueError:
            self.page = 1
        self.rows = t.rows(conn.execute(f"{sql} LIMIT ? OFFSET ?", (*args, per_page, (self.page - 1) * per_page)))

    def url(self, n):
        q = {k: v[0] for k, v in self.params.items()}
        q[self.key] = n
        return "/?" + urlencode(q) + f"#{self.key}"

    def html(self):
        if self.pages <= 1:
            return ""
        nums = sorted({1, self.pages, *range(max(1, self.page - 2), min(self.pages, self.page + 2) + 1)})
        parts, prev = [], 0
        for n in nums:
            if n - prev > 1:
                parts.append("<span>…</span>")
            parts.append(f'<span class=cur>{n}</span>' if n == self.page else f'<a href="{self.url(n)}">{n}</a>')
            prev = n
        first = (self.page - 1) * self.per + 1
        return (f'<div class=pager><span>{first}–{min(self.total, first + self.per - 1)} de {self.total}</span>'
                f'{"<a href=" + chr(34) + self.url(self.page - 1) + chr(34) + ">‹</a>" if self.page > 1 else ""}'
                f'{"".join(parts)}'
                f'{"<a href=" + chr(34) + self.url(self.page + 1) + chr(34) + ">›</a>" if self.page < self.pages else ""}</div>')


def table(headers, rows_html, empty="Nada por aquí.", pager=None, anchor=None):
    aid = f' id="{anchor}"' if anchor else ""
    if not rows_html:
        return f'<div class=card{aid}><div class=empty>{empty}</div></div>'
    th = "".join(f"<th class={'num' if h.startswith('#') else ''}>{e(h.lstrip('#'))}</th>" for h in headers)
    return (f'<div class="card wrap"{aid}><table><tr>{th}</tr>{"".join(rows_html)}</table>'
            f'{pager.html() if pager else ""}</div>')


def steps_chips(steps):
    return "".join(f'<span class="chip s-{e(s["status"])}" title="{e(s["name"])} — {e(s["status"])}">'
                   f'{s["seq"]}. {e(STEP_LABEL.get(s["type"], s["type"]))}</span>' for s in steps)


def platform_stats(conn):
    return t.rows(conn.execute(
        f"SELECT a.platform, COUNT(*) n, "
        f"SUM(a.status IN {RESPONDED}) resp, SUM({ADVANCED_SQL}) adv, SUM(a.status='rejected') rej "
        f"FROM applications a GROUP BY a.platform ORDER BY n DESC"))


def mvp_block(stats):
    eligible = [s for s in stats if s["n"] >= MVP_MIN_APPS and s["platform"] != "Other"]
    if not eligible:
        return (f'<div class=mvp><span class=sub>Plataforma MVP</span><br>Aún no hay suficientes datos '
                f'(se necesita al menos {MVP_MIN_APPS} aplicaciones en una plataforma).</div>')
    best = max(eligible, key=lambda s: (wilson_low(s["adv"], s["n"]), s["adv"], s["n"]))
    rate = best["adv"] / best["n"]
    return (f'<div class=mvp><span class=sub>Plataforma MVP · la que más convierte a procesos reales '
            f'(mín. {MVP_MIN_APPS} aplicaciones, ajustado por tamaño de muestra)</span><br>'
            f'<b>{e(best["platform"])}</b> — {rate:.0%} de tus aplicaciones ahí avanzaron a una etapa real '
            f'({best["adv"]} de {best["n"]}); {best["resp"] / best["n"]:.0%} recibieron respuesta.</div>')


def render_home(conn, params):
    total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    by_status = dict(conn.execute("SELECT status, COUNT(*) FROM applications GROUP BY status").fetchall())
    responded = sum(by_status.get(s, 0) for s in RESPONDED)
    active = sum(by_status.get(s, 0) for s in ACTIVE)
    week = conn.execute("SELECT COUNT(*) FROM applications WHERE applied_at >= date('now','localtime','-7 days')").fetchone()[0]
    last_email = conn.execute("SELECT MAX(finished_at) FROM runs WHERE kind='email_check'").fetchone()[0]
    stats = platform_stats(conn)

    kpis = "".join(f'<div class=kpi><b>{v}</b><span>{l}</span></div>' for v, l in [
        (total, "aplicaciones"), (week, "últimos 7 días"), (active, "procesos activos"),
        (f"{responded / total:.0%}" if total else "–", "tasa de respuesta"),
        (by_status.get("rejected", 0), "rechazos"), (by_status.get("offer", 0) + by_status.get("hired", 0), "ofertas")])

    tasks = Pager(conn, params, "tp",
                  "SELECT tk.*, c.name company FROM tasks tk LEFT JOIN applications a ON a.id=tk.application_id "
                  "LEFT JOIN companies c ON c.id=a.company_id WHERE tk.status='open' AND tk.owner='user' "
                  "ORDER BY tk.due_at IS NULL, tk.due_at", per_page=10)
    task_rows = [f'<tr><td class="{due_class(x["due_at"])}">{e(x["due_at"] or "—")}</td>'
                 f'<td>{e(x["title"])}{"<br>" + link(x["link"], "abrir") if x["link"] else ""}</td>'
                 f'<td><a href="/app/{x["application_id"]}">{e(x["company"])}</a></td>'
                 f'<td><form method=post action="/task/{x["id"]}/done"><button>Hecho</button></form></td></tr>'
                 for x in tasks.rows]

    agenda = Pager(conn, params, "ap",
                   "SELECT s.*, c.name company, a.id app_id FROM steps s JOIN applications a ON a.id=s.application_id "
                   "JOIN companies c ON c.id=a.company_id WHERE s.status IN ('scheduled','to_schedule') "
                   "ORDER BY COALESCE(s.scheduled_at, s.deadline_at) IS NULL, COALESCE(s.scheduled_at, s.deadline_at)",
                   per_page=10)
    agenda_rows = []
    for s in agenda.rows:
        when = s["scheduled_at"] or (f'antes de {s["deadline_at"]}' if s["deadline_at"] else "por agendar")
        agenda_rows.append(f'<tr><td class="{due_class(s["scheduled_at"] or s["deadline_at"])}">{e(when)}</td>'
                           f'<td><a href="/app/{s["app_id"]}">{e(s["company"])}</a></td>'
                           f'<td>{e(s["name"])}<br><span class=sub>{e(STEP_LABEL.get(s["type"]))}'
                           f'{" · " + str(s["duration_min"]) + " min" if s["duration_min"] else ""}</span></td>'
                           f'<td>{link(s["link"], "link") if s["link"] else ""}</td></tr>')

    procs = Pager(conn, params, "pp",
                  "SELECT a.id, c.name company, a.position, a.status FROM applications a "
                  "JOIN companies c ON c.id=a.company_id WHERE a.status IN ('screening','needs_info','in_process','offer') "
                  "ORDER BY CASE a.status WHEN 'offer' THEN 0 WHEN 'in_process' THEN 1 WHEN 'screening' THEN 2 ELSE 3 END, "
                  "a.updated_at DESC", per_page=10)
    proc_rows = []
    for p in procs.rows:
        steps = t.rows(conn.execute("SELECT * FROM steps WHERE application_id=? ORDER BY seq", (p["id"],)))
        proc_rows.append(f'<tr><td><a href="/app/{p["id"]}">{e(p["company"])}</a><br><span class=sub>{e(p["position"])}</span></td>'
                         f'<td><span class=chip>{e(STATUS_LABEL[p["status"]])}</span></td>'
                         f'<td>{steps_chips(steps) or "<span class=sub>sin steps registrados</span>"}</td></tr>')

    mx_rate = max([s["adv"] / s["n"] for s in stats] or [1]) or 1
    plat_rows = [f'<tr><td>{e(s["platform"])}</td><td class=num>{s["n"]}</td><td class=num>{s["resp"]}</td>'
                 f'<td class=num>{s["adv"]}</td><td class=num>{s["rej"]}</td>'
                 f'<td class=num>{s["adv"] / s["n"]:.0%}</td>'
                 f'<td style="width:22%"><div class=bar style="width:{s["adv"] / s["n"] / mx_rate * 100:.0f}%"></div></td></tr>'
                 for s in sorted(stats, key=lambda s: (-wilson_low(s["adv"], s["n"]), -s["n"]))]

    mx = max(by_status.values() or [1])
    status_rows = [f'<tr><td>{e(STATUS_LABEL[s])}</td><td class=num>{n}</td>'
                   f'<td style="width:55%"><div class=bar style="width:{n / mx * 100:.0f}%"></div></td></tr>'
                   for s, n in sorted(by_status.items(), key=lambda x: -x[1])]

    events = Pager(conn, params, "ep",
                   "SELECT ev.*, c.name company FROM events ev JOIN applications a ON a.id=ev.application_id "
                   "JOIN companies c ON c.id=a.company_id WHERE ev.type <> 'applied' "
                   "ORDER BY COALESCE(ev.occurred_at, ev.recorded_at) DESC, ev.id DESC", per_page=10)
    ev_rows = [f'<tr class=ev><td class=when>{e((x["occurred_at"] or "")[:10])}</td>'
               f'<td><a href="/app/{x["application_id"]}">{e(x["company"])}</a></td><td><span class=chip>{e(x["type"])}</span> '
               f'{e(x["summary"][:220])}{"…" if len(x["summary"]) > 220 else ""}</td></tr>' for x in events.rows]

    # All applications: server-side filters so search covers every page, not just the visible one.
    fq = params.get("q", [""])[0].strip()
    fs = params.get("status", [""])[0]
    fp = params.get("platform", [""])[0]
    where, args = ["1=1"], []
    if fq:
        where.append("(c.name LIKE ? OR a.position LIKE ? OR c.name_norm LIKE ? OR a.position_norm LIKE ?)")
        args += [f"%{fq}%", f"%{fq}%", f"%{t.norm_company(fq)}%", f"%{t.norm_position(fq)}%"]
    if fs in STATUS_LABEL:
        where.append("a.status=?")
        args.append(fs)
    if fp:
        where.append("a.platform=?")
        args.append(fp)
    apps = Pager(conn, params, "p",
                 "SELECT a.id, c.name company, a.position, a.platform, a.status, a.applied_at FROM applications a "
                 f"JOIN companies c ON c.id=a.company_id WHERE {' AND '.join(where)} "
                 "ORDER BY a.applied_at IS NULL, a.applied_at DESC, a.id DESC", args, per_page=25)
    app_rows = [f'<tr><td class=when>{e(x["applied_at"] or "—")}</td><td><a href="/app/{x["id"]}">{e(x["company"])}</a></td>'
                f'<td>{e(x["position"])}</td><td>{e(x["platform"])}</td>'
                f'<td><span class=chip>{e(STATUS_LABEL[x["status"]])}</span></td></tr>' for x in apps.rows]
    status_opts = "".join(f'<option value="{k}"{" selected" if k == fs else ""}>{v}</option>' for k, v in STATUS_LABEL.items())
    plat_opts = "".join(f'<option{" selected" if s["platform"] == fp else ""}>{e(s["platform"])}</option>' for s in stats)

    name = person_name()
    body = f"""
<h1>Job Hunt{" · " + e(name) if name else ""}</h1>
<div class=sub>Actualizado {datetime.now():%Y-%m-%d %H:%M} · última revisión de correo: {e(last_email or "ninguna aún")}</div>
<div class=kpis>{kpis}</div>
{mvp_block(stats)}
<h2>Qué me toca</h2>{table(["Para", "Pendiente", "Empresa", ""], task_rows, "Sin pendientes.", tasks, "tp")}
<h2>Agenda de steps</h2>{table(["Cuándo", "Empresa", "Step", ""], agenda_rows, "Nada agendado.", agenda, "ap")}
<h2>Procesos activos</h2>{table(["Empresa", "Estado", "Steps"], proc_rows, pager=procs, anchor="pp")}
<div class=grid2>
<div><h2>Ranking de plataformas</h2>{table(["Plataforma", "#Apps", "#Resp.", "#Avanzan", "#Rech.", "#% avance", ""], plat_rows)}</div>
<div><h2>Por estado</h2>{table(["Estado", "#N", ""], status_rows)}</div>
</div>
<h2>Actividad reciente</h2>{table(["Fecha", "Empresa", "Evento"], ev_rows, pager=events, anchor="ep")}
<h2 id=p>Todas las aplicaciones</h2>
<form class=filters method=get action="/#p">
<input type=search name=q value="{e(fq)}" placeholder="Empresa o puesto…">
<select name=status><option value="">Todos los estados</option>{status_opts}</select>
<select name=platform><option value="">Todas las plataformas</option>{plat_opts}</select>
<button>Filtrar</button>{' <a href="/#p">limpiar</a>' if fq or fs or fp else ""}
</form>
{table(["Fecha", "Empresa", "Puesto", "Plataforma", "Estado"], app_rows, "Sin resultados.", apps)}"""
    return page("Job Hunt", body)


def render_app(conn, app_id):
    d = t.app_detail(conn, app_id)
    if not d:
        return None
    facts = [("Estado", STATUS_LABEL[d["status"]]), ("Aplicada", d["applied_at"]), ("Plataforma", d["platform"]),
             ("ATS", d["ats"]), ("Modalidad", d["modality"]), ("Seniority", d["seniority"]), ("Salario", d["salary_text"]),
             ("CV", d["cv_used"]), ("Importado de", d["import_ref"])]
    facts_html = "".join(f'<div class=kpi><span>{k}</span><b style="font-size:15px">{e(v)}</b></div>' for k, v in facts if v)
    step_rows = [f'<tr><td>{s["seq"]}</td><td>{e(s["name"])}<br><span class=sub>{e(STEP_LABEL.get(s["type"]))}</span></td>'
                 f'<td class="s-{e(s["status"])}">{e(s["status"])}</td><td>{e(s["scheduled_at"] or s["deadline_at"] or "")}</td>'
                 f'<td>{e(s["result"])}{"<br>" + link(s["link"], "link") if s["link"] else ""}'
                 f'{"<br><span class=sub>" + e(s["details"]) + "</span>" if s["details"] else ""}</td></tr>' for s in d["steps"]]
    task_rows = [f'<tr><td class="{due_class(x["due_at"]) if x["status"] == "open" else ""}">{e(x["due_at"] or "—")}</td>'
                 f'<td>{e(x["title"])}</td><td>{e(x["status"])}</td></tr>' for x in d["tasks"]]
    ans_rows = [f'<tr><td>{e(x["question"])}</td><td>{e(x["answer"])}</td><td>{e(x["honesty_note"])}</td></tr>'
                for x in d["screening_answers"]]
    ev_rows = [f'<tr class=ev><td class=when>{e(x["occurred_at"] or "—")}</td><td><span class=chip>{e(x["type"])}</span></td>'
               f'<td><pre>{e(x["summary"])}</pre>{"<br><i>“" + e(x["quote"]) + "”</i>" if x["quote"] else ""}</td></tr>'
               for x in d["events"]]
    note = lambda title, text: (f"<h2>{title}</h2><div class=card><div class=empty style='color:inherit'>{e(text)}</div></div>"
                                if text else "")
    body = f"""<a href="/">← Volver</a>
<h1 style="margin-top:12px">{e(d["company"])}</h1><div class=sub>{e(d["position"])}{" · " + link(d["job_url"], "ver vacante") if d["job_url"] else ""}</div>
<div class=kpis>{facts_html}</div>
{note("Notas de fit", d["fit_notes"])}{note("Ojo (honestidad)", d["honesty_flags"])}
<h2>Steps</h2>{table(["#", "Step", "Estado", "Cuándo", "Resultado / link"], step_rows, "Sin steps registrados.")}
<h2>Pendientes</h2>{table(["Para", "Pendiente", "Estado"], task_rows, "Sin pendientes.")}
<h2>Respuestas de screening</h2>{table(["Pregunta", "Respuesta", "Nota"], ans_rows, "Sin respuestas registradas.")}
<h2>Historial</h2>{table(["Fecha", "Tipo", "Detalle"], ev_rows)}"""
    return page(d["company"], body)


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        conn = t.connect()
        try:
            if url.path == "/":
                return self.send(200, render_home(conn, parse_qs(url.query)))
            m = re.fullmatch(r"/app/(\d+)", url.path)
            if m and (html_ := render_app(conn, int(m.group(1)))):
                return self.send(200, html_)
            if url.path == "/api/pending":
                return self.send(200, json.dumps(t.cmd_pending(conn, None), default=str), "application/json")
            self.send(404, page("No encontrado", "<a href='/'>← Volver</a><h1>No encontrado</h1>"))
        finally:
            conn.close()

    def do_POST(self):
        m = re.fullmatch(r"/task/(\d+)/done", urlparse(self.path).path)
        if not m:
            return self.send(404, "not found", "text/plain")
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).hostname not in ("127.0.0.1", "localhost"):
            return self.send(403, "forbidden", "text/plain")   # block cross-site form posts
        conn = t.connect()
        try:
            with conn:
                conn.execute("UPDATE tasks SET status='done', done_at=? WHERE id=? AND status='open'", (t.now(), int(m.group(1))))
            t.backup(conn)
        finally:
            conn.close()
        self.send_response(303)
        self.send_header("Location", self.headers.get("Referer") or "/")
        self.end_headers()

    def log_message(self, *a):
        pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    a = p.parse_args()
    print(f"Dashboard: http://127.0.0.1:{a.port}")
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
