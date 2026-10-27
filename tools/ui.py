"""Local, read-only web UI for browsing the corpus.

  python3 tools/ui.py                 # http://127.0.0.1:8766
  python3 tools/ui.py --port 9000

Opens db/case.sqlite read-only on every request (reflects the latest build.py) and
serves the originals in sources/ under /file/. Writes no files.
"""
import argparse
import html
import mimetypes
import re
import shutil
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit

from search import search, citation
from common import DB, SOURCES, RE_PID, normalize
from ingest import VIDEO_WINDOW

PER_PAGE = 20
TRANSCRIPTS = SOURCES / "audiovisual" / "transcripts"
LAYER2_TABLES = ["extraction", "extraction_item", "entity", "alias", "mention", "relation", "event",
                 "claim", "citation", "statement", "expert_report", "evidence_item", "custody", "topic",
                 "hypothesis", "ach"]
WHO_FILLS = {"entity": "WP5 (people and aliases) and WP6 (organizations, places, objects, phone lines)",
             "extraction": "the EXT-* tasks (analysis/extraction/&lt;doc_id&gt;.jsonl) when tools/build.py runs"}

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1f;--mut:#6b6b70;--line:#e2dfd8;--acc:#1f5fbf;--mark:#ffe08a;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--fg:#e6e4df;--mut:#9b9ba1;--line:#2d2d32;
 --acc:#8db6ff;--mark:#5e4f12;--card:#1b1b1e}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
nav{position:sticky;top:0;z-index:1;background:var(--bg);border-bottom:1px solid var(--line)}
nav div{max-width:1100px;margin:0 auto;padding:8px 16px;display:flex;flex-wrap:wrap;gap:4px 16px;align-items:center}
nav b{margin-right:8px}nav form{margin-left:auto}
main{max-width:1100px;margin:0 auto;padding:16px 16px 64px}
h1{font-size:1.45rem;line-height:1.25;margin:.4em 0 .6em;text-wrap:balance;overflow-wrap:anywhere}
h2{font-size:1.1rem;margin:1.8em 0 .5em}
.mut{color:var(--mut)}.peq{font-size:.875rem}
.texto{white-space:pre-wrap;overflow-wrap:anywhere;max-width:78ch;line-height:1.65;background:var(--card);
 border:1px solid var(--line);border-radius:6px;padding:16px 20px;margin:0}
table{border-collapse:collapse;width:100%;font-size:.9rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;vertical-align:top;padding:6px 8px;border-bottom:1px solid var(--line)}
th{font-weight:600;color:var(--mut)}
input,select,button{font:inherit;font-size:.9rem;padding:4px 8px;border:1px solid var(--line);border-radius:5px;
 background:var(--card);color:var(--fg)}
form.filtros{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 16px}
.hit{margin:0 0 20px;max-width:80ch}.hit p{margin:4px 0}
code{font-size:.85em;overflow-wrap:anywhere}code.cita{user-select:all;color:var(--mut)}
mark{background:var(--mark);color:inherit;border-radius:2px}
.pag{display:flex;gap:16px;margin:16px 0}
.vacio{border:1px dashed var(--line);border-radius:6px;padding:12px 16px;color:var(--mut);max-width:78ch}
dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;font-size:.9rem}dt{color:var(--mut)}dd{margin:0;overflow-wrap:anywhere}
"""
NAV = [("/", "Home"), ("/search", "Search"), ("/index", "Index"), ("/entities", "Entities"),
       ("/extraction", "Extraction"), ("/transcripts", "Transcripts"), ("/sources", "Sources")]


def e(x):
    return html.escape("" if x is None else str(x))


def url(path, **q):
    q = {k: v for k, v in q.items() if v not in (None, "")}
    return e(path + ("?" + urlencode(q) if q else ""))


def a_page(doc_id, n, text=None):
    return f'<a href="/p/{quote(doc_id)}/{n}">{e(text or f"{doc_id} · {n}")}</a>'


def a_pid(pid):
    m = RE_PID.match(pid or "")
    return a_page(m[1], int(m[3]), pid) if m else e(pid)


def a_external(u, text):
    return f'<a href="{e(u)}" rel="noreferrer">{e(text)}</a>' if re.match(r"https?://", u or "") else e(u)


RE_YOUTUBE = re.compile(r"https://(www\.)?youtube\.com/watch\?v=[A-Za-z0-9_-]+$")


def hms(s):
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def link_times(text_html, yt):
    """Turns each [H:MM:SS] in the (already escaped) text into a link to that second of the video."""
    def stamp(x):
        s = int(x[1]) * 3600 + int(x[2]) * 60 + int(x[3])
        return f'<a href="{e(yt)}&amp;t={s}s" rel="noreferrer">{x[0]}</a>'
    return re.sub(r"\[(\d+):(\d\d):(\d\d)\]", stamp, text_html)


def exists(path):
    """True if the file (path starts with sources/) is in this copy; the public clone has text only."""
    return (SOURCES.parent / path).is_file()


def a_file(path, text, page=None):
    """Link to the original (path starts with sources/). PDFs open at the given page.
    Plain text with a note when the file is not in this copy."""
    if not exists(path):
        return f'{e(text)} <span class="mut">(not in this copy)</span>'
    rel = path.removeprefix("sources/")
    frag = f"#page={page}" if page and path.lower().endswith(".pdf") else ""
    return f'<a href="/file/{quote(rel)}{frag}">{e(text)}</a>'


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{c}</th>" for c in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def pager(path, q, page, more):
    prev = f'<a href="{url(path, **q, page=page - 1)}">← Previous</a>' if page > 1 else ""
    nxt = f'<a href="{url(path, **q, page=page + 1)}">Next →</a>' if more else ""
    return f'<div class="pag">{prev}<span class="mut">Page {page}</span>{nxt}</div>'


def options(values, current, all_="All"):
    return f'<option value="">{all_}</option>' + "".join(
        f'<option value="{e(v)}"{" selected" if v == current else ""}>{e(t)}</option>' for v, t in values)


def document(con, doc_id):
    return con.execute("SELECT doc_id, type, title, date, original_path, text_path, source_url, source_level, n_pages, "
                       "n_text_pages, text_status, anchor, sha256 FROM document WHERE doc_id=?", (doc_id,)).fetchone()


# ---------- pages ----------

def home(con, q):
    rows = con.execute(
        "SELECT substr(original_path, 9, instr(substr(original_path, 9), '/') - 1) AS c, count(*), "
        "sum(coalesce(n_text_pages, 0)), group_concat(DISTINCT text_status) FROM document GROUP BY c ORDER BY c").fetchall()
    t1 = table(["Folder", "Documents", "Pages or sections with text", "Text status"],
               [[f'<a href="{url("/docs", folder=c)}">{e(c)}</a>', f"{d:,}", f"{p:,}", e(s)] for c, d, p, s in rows])
    present = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    t2 = table(["Table", "Rows"], [[f"<code>{t}</code>", f"{con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]:,}"]
                                   for t in LAYER2_TABLES if t in present])
    filings = con.execute("SELECT count(*) FROM filing").fetchone()[0]
    return "García Belsunce corpus", f"""<h1>García Belsunce case corpus</h1>
<p class="mut">Read-only browser over <code>db/case.sqlite</code>. Citations are written
<code>[[doc_id#pN]]</code>; the PDF page is not the folio.</p>
<h2>Loaded sources</h2>{t1}
<h2>Case-file index</h2><p><a href="/index">{filings:,} filings</a> from <code>INDICE-por-cuerpos.tsv</code>.</p>
<h2>Layer 2 (analysis)</h2>{t2}
<p class="peq mut">A table at 0 fills once its work package writes files to <code>analysis/</code> and <code>tools/build.py</code> runs.</p>"""


def docs(con, q):
    folder = q.get("folder", "")
    rows = con.execute("SELECT doc_id, title, date, n_text_pages, text_status FROM document "
                       "WHERE original_path LIKE ? ORDER BY doc_id", (f"sources/{folder}/%",)).fetchall()
    t = table(["doc_id", "Title", "Date", "Pages", "Status"],
              [[f'<a href="/doc/{quote(d)}">{e(d)}</a>', e(ti), e(f), e(n), e(s)] for d, ti, f, n, s in rows])
    return f"Documents: {folder}", f"<h1>sources/{e(folder)}</h1><p class='mut'>{len(rows):,} documents</p>{t}"


def search_page(con, q):
    text, source, doc, mode = q.get("q", "").strip(), q.get("source", ""), q.get("doc", ""), q.get("mode", "")
    page = max(1, int(q.get("page", "1")) if q.get("page", "1").isdigit() else 1)
    types = [(t, t) for t, in con.execute("SELECT DISTINCT type FROM document ORDER BY 1")]
    modes = [("variants", "With spelling variants"), ("sub", "Substring (trigrams)"), ("fts", "FTS5 syntax")]
    form = f"""<form class="filtros" action="/search"><input name="q" value="{e(text)}" size="34" placeholder="Phrase, name, time…" autofocus>
<select name="source" aria-label="Source">{options(types, source, "All sources")}</select>
<input name="doc" value="{e(doc)}" size="10" placeholder="doc_id: exp-c05" aria-label="doc_id prefix">
<select name="mode" aria-label="Mode">{options(modes, mode, "Exact phrase")}</select><button>Search</button></form>"""
    if not text:
        return "Search", f"""<h1>Search</h1>{form}<p class="mut">Ignores accents and case. If the exact phrase finds
nothing, spelling variants and then substrings are tried, as in <code>search.py</code>. Primary sources come first.
A pid (<code>exp-c01#p171</code>) opens that page directly.</p>"""
    m = RE_PID.match(text)
    if m:
        raise Redirect(f"/p/{quote(m[1])}/{m[3]}")
    a = SimpleNamespace(fts=mode == "fts", sub=mode == "sub", variants=mode == "variants",
                        doc=doc or None, type=source or None, limit=page * PER_PAGE)
    try:
        used, expr, total, rows, by_type, variants = search(con, text, a, ("\x02", "\x03"))
    except sqlite3.OperationalError as err:
        return "Search", f'{form}<p class="vacio">Invalid query: {e(err)}</p>'
    out = [f"<h1>Search: {e(text)}</h1>", form,
           f'<p class="mut peq">{total:,} pages · mode <b>{e(used)}</b> · expression <code>{e(expr)}</code><br>'
           + " · ".join(f'<a href="{url("/search", q=text, doc=doc, mode=mode, source=t)}">{e(t)} {c:,}</a>' for t, c in by_type) + "</p>"]
    for w, vs in variants.items():
        out.append(f'<p class="peq mut">Variants of “{e(w)}” in the corpus: ' + ", ".join(
            f'<a href="{url("/search", q=t, source=source, doc=doc)}">{e(t)}</a> ({c})' for t, c in vs) + "</p>")
    for pid, folio, type_, snip, lit in rows[(page - 1) * PER_PAGE:]:
        d, n = pid.split("#")[0], int(re.sub(r"\D", "", pid.split("#")[1]))
        s = e(" ".join(snip.split())).replace("\x02", "<mark>").replace("\x03", "</mark>")
        fs = f' · fs. {e(folio)}?' if folio else ""
        out.append(f'<div class="hit"><p>{a_page(d, n, pid)} <span class="mut peq">{e(type_)}{fs}</span></p>'
                   f'<p>{s}</p><p><code class="cita">{e(citation(pid, lit, used))}</code></p></div>')
    if not rows:
        out.append('<p class="vacio">No results.</p>')
    out.append(pager("/search", dict(q=text, source=source, doc=doc, mode=mode), page, total > page * PER_PAGE))
    return f"Search: {text}", "".join(out)


def doc_page(con, doc_id):
    d = document(con, doc_id)
    if not d:
        raise NotFound
    _, type_, title, date, path, text_path, src_url, level, n_pages, n_text, status, anchor, sha = d
    meta = [("Type", type_), ("Source level", level), ("Date", date), ("Text status", status),
            ("Pages in the original", n_pages), ("With text", n_text), ("sha256", sha)]
    dl = "".join(f"<dt>{k}</dt><dd>{e(v)}</dd>" for k, v in meta if v not in (None, ""))
    dl += f"<dt>Original</dt><dd>{a_file(path, path)}</dd>"
    if text_path and text_path != path:
        dl += f"<dt>Text</dt><dd>{a_file(text_path, text_path)}</dd>"
    if src_url:
        dl += f"<dt>Source URL</dt><dd>{a_external(src_url, src_url)}</dd>"
    extra = []
    nf = con.execute("SELECT count(*) FROM filing WHERE doc_id=?", (doc_id,)).fetchone()[0]
    nx = con.execute("SELECT count(*) FROM extraction WHERE doc_id=?", (doc_id,)).fetchone()[0]
    if nf:
        extra.append(f'<a href="{url("/index", volume=doc_id)}">{nf} filings in the index</a>')
    if nx:
        extra.append(f'<a href="{url("/extraction", doc=doc_id)}">{nx} extracted filings</a>')
    pages = con.execute("SELECT n, folio, substr(text, 1, 400) FROM page WHERE doc_id=? ORDER BY n", (doc_id,)).fetchall()
    rows = [[a_page(doc_id, n, f"#{anchor}{n}"), e(f), e(" ".join(t.split())[:140])] for n, f, t in pages]
    listing = table(["Page", "Folio?", "Opening"], rows) if rows else f'<p class="vacio">No text yet ({e(status)}).</p>'
    return doc_id, f"""<p class="mut peq">{e(doc_id)}</p><h1>{e(title or doc_id)}</h1><dl>{dl}</dl>
<p>{" · ".join(extra)}</p><h2>Pages and sections</h2>{listing}"""


def p_page(con, doc_id, n):
    d = document(con, doc_id)
    row = con.execute("SELECT pid, folio, text, source_file, line, t_start FROM page WHERE doc_id=? AND n=?", (doc_id, n)).fetchone()
    if not d or not row:
        raise NotFound
    pid, folio, text, source_file, line, t_start = row
    yt = d[6] if t_start is not None and RE_YOUTUBE.match(d[6] or "") else None
    prev = con.execute("SELECT max(n) FROM page WHERE doc_id=? AND n<?", (doc_id, n)).fetchone()[0]
    nxt = con.execute("SELECT min(n) FROM page WHERE doc_id=? AND n>?", (doc_id, n)).fetchone()[0]
    nav = " · ".join(x for x in [a_page(doc_id, prev, "← Previous") if prev else "",
                                 f'<a href="/doc/{quote(doc_id)}">Document</a>',
                                 a_page(doc_id, nxt, "Next →") if nxt else ""] if x)
    # the PDF at this page if this copy has it (the public clone does not), else the text file; then the source URL
    if d[4].lower().endswith(".pdf") and exists(d[4]):
        info = [a_file(d[4], "Open the original at this page", n)]
    else:
        info = [a_file(source_file or d[4], "Open the text file")]
    if d[6] and not yt:
        info.append(a_external(d[6], "Open the source"))
    info.insert(0, f"<code class='cita'>[[{e(pid)}]]</code>")
    if yt:
        info.insert(1, f'<a href="{e(yt)}&amp;t={t_start}s" rel="noreferrer">Watch on YouTube from {hms(t_start)}</a>'
                       f' <span class="mut">(segment {hms(t_start)}–{hms(t_start + VIDEO_WINDOW)})</span>')
    if folio:
        info.append(f"fs. {e(folio)}? <span class='mut'>(detected automatically: check it against the image)</span>")
    if line and source_file:
        info.append(f"<span class='mut'>{e(source_file)}, line {e(line)}</span>")
    out = [f'<p class="mut peq">{e(d[2] or doc_id)} · {nav}</p><h1>{e(pid)}</h1><p class="peq">{" · ".join(info)}</p>',
           f'<pre class="texto">{link_times(e(text), yt) if yt else e(text)}</pre><p class="peq">{nav}</p>']
    filings = con.execute("SELECT subject, page, page_end, filing_type FROM filing WHERE doc_id=? AND "
                          "(page=? OR (page<=? AND page_end>=?)) ORDER BY page", (doc_id, n, n, n)).fetchall()
    if filings:
        out.append("<h2>Case-file index</h2>" + table(["Subject", "Page", "Type"], [
            [e(s), e(f"{p}-{pe}" if pe else p), e(ft)] for s, p, pe, ft in filings]))
    for x in con.execute("SELECT ext_id, page_start, page_end, folio, type, date, summary, agent FROM extraction "
                         "WHERE doc_id=? AND ? BETWEEN page_start AND page_end", (doc_id, n)).fetchall():
        items = con.execute("SELECT kind, text, role, value, pid FROM extraction_item WHERE ext_id=? "
                            "ORDER BY kind, pid", (x[0],)).fetchall()
        out.append(f"<h2>Extracted filing: {e(x[4])}, pages {a_page(doc_id, x[1], x[1])}–{a_page(doc_id, x[2], x[2])}</h2>"
                   f"<p>{e(x[6])}</p><p class='mut peq'>Date {e(x[5] or 'not stated')} · folio {e(x[3] or 'not stated')}"
                   f" · {e(x[7])}</p>" + (table(["Kind", "Text", "Role or value", "Page"], [
                       [e(k), e(t), e(r or v), e(p)] for k, t, r, v, p in items]) if items else ""))
    ment = con.execute("SELECT m.literal_text, m.status, m.ent_id, en.canonical_name FROM mention m "
                       "LEFT JOIN entity en USING (ent_id) WHERE m.pid=? ORDER BY 1", (pid,)).fetchall()
    if ment:
        out.append("<h2>Mentions</h2>" + table(["Literal form", "Entity", "Status"], [
            [e(t), f'<a href="/entity/{quote(i)}">{e(cn or i)}</a>' if i else "<span class='mut'>Unresolved</span>", e(s)]
            for t, s, i, cn in ment]))
    return pid, "".join(out)


def index(con, q):
    volume, text, order = q.get("volume", ""), q.get("q", ""), q.get("order", "volume")
    order_sql = {"page": "page, doc_id", "subject": "subject COLLATE NOCASE"}.get(order, "doc_id IS NULL, doc_id, page")
    rows = con.execute(f"SELECT doc_id, page, page_end, subject, filing_type, original_volume, doc_resolution, candidates "
                       f"FROM filing ORDER BY {order_sql}").fetchall()
    if volume:
        rows = [r for r in rows if (r[0] or "ambiguous") == volume]
    if text:
        rows = [r for r in rows if normalize(text) in normalize(r[3])]
    volumes = [(v or "ambiguous", v or "Ambiguous (no doc_id)") for v, in
               con.execute("SELECT DISTINCT doc_id FROM filing ORDER BY doc_id IS NULL, doc_id")]
    filters = dict(volume=volume, q=text)
    head = [f'<a href="{url("/index", **filters, order=o)}">{t}</a>' for o, t in
            [("volume", "Volume"), ("page", "Page"), ("subject", "Subject")]] + ["Type"]

    def page_cell(d, p, pe, cand):
        if d and p:
            return a_page(d, p, f"{p}-{pe}" if pe else p)
        return e(p) + (f' <span class="mut peq">({e(cand)})</span>' if cand else "")
    t = table(head, [[e(d or v), page_cell(d, p, pe, cand), e(s), e(ft)] for d, p, pe, s, ft, v, r, cand in rows])
    return "Case-file index", f"""<h1>Case-file index</h1>
<form class="filtros" action="/index"><select name="volume" aria-label="Volume">{options(volumes, volume)}</select>
<input name="q" value="{e(text)}" placeholder="Subject contains…" aria-label="Subject"><input type="hidden" name="order" value="{e(order)}">
<button>Filter</button></form><p class="mut peq">{len(rows):,} filings. “Page” is the PDF page, not the folio.</p>{t}"""


def entities(con, q):
    n = con.execute("SELECT count(*) FROM entity").fetchone()[0]
    unres = con.execute("SELECT literal_text, count(*) FROM mention WHERE ent_id IS NULL GROUP BY 1 "
                        "ORDER BY 2 DESC LIMIT 60").fetchall()
    extra = ("<h2>Mentioned forms with no entity yet</h2>" + table(["Literal form", "Mentions"], [
        [f'<a href="{url("/search", q=t)}">{e(t)}</a>', c] for t, c in unres])) if unres else ""
    if not n:
        return "Entities", (f'<h1>Entities</h1><p class="vacio">No entities yet. They are loaded by {WHO_FILLS["entity"]};'
                            ' WP7 links mentions to each entity. They appear here after <code>tools/build.py</code>.</p>' + extra)
    kind, text = q.get("kind", ""), q.get("q", "")
    rows = con.execute(
        "SELECT ent_id, kind, canonical_name, role_summary, merged_into, "
        "(SELECT group_concat(alias, '; ') FROM alias a WHERE a.ent_id=en.ent_id), "
        "(SELECT count(*) FROM mention m WHERE m.ent_id=en.ent_id) FROM entity en "
        "WHERE (?='' OR kind=?) ORDER BY kind, canonical_name", (kind, kind)).fetchall()
    if text:
        rows = [r for r in rows if normalize(text) in normalize(f"{r[2]} {r[5] or ''} {r[0]}")]
    kinds = [(k, k) for k, in con.execute("SELECT DISTINCT kind FROM entity ORDER BY 1")]
    t = table(["Entity", "Kind", "Role", "Aliases", "Mentions"], [
        [f'<a href="/entity/{quote(i)}">{e(cn)}</a>' + (f' <span class="mut peq">→ {e(mi)}</span>' if mi else ""),
         e(k), e(r), e(al), m] for i, k, cn, r, mi, al, m in rows])
    return "Entities", f"""<h1>Entities</h1><form class="filtros" action="/entities">
<select name="kind" aria-label="Kind">{options(kinds, kind, "All kinds")}</select>
<input name="q" value="{e(text)}" placeholder="Name or alias" aria-label="Name or alias"><button>Filter</button></form>
<p class="mut peq">{len(rows):,} entities</p>{t}{extra}"""


def entity(con, ent_id):
    en = con.execute("SELECT ent_id, kind, canonical_name, role_summary, notes, merged_into, created_by FROM entity "
                     "WHERE ent_id=?", (ent_id,)).fetchone()
    if not en:
        raise NotFound
    aliases = con.execute("SELECT alias, type, confidence, source_pid FROM alias WHERE ent_id=? ORDER BY alias", (ent_id,)).fetchall()
    ment = con.execute("SELECT m.pid, p.doc_id, p.n, m.literal_text, m.quote, m.status FROM mention m JOIN page p USING (pid) "
                       "WHERE m.ent_id=? ORDER BY p.doc_id, p.n LIMIT 1000", (ent_id,)).fetchall()
    n_m, n_d, d_min, d_max = con.execute(
        "SELECT count(*), count(DISTINCT doc_id), min(f), max(f) FROM (SELECT p.doc_id, CASE WHEN d.date GLOB "
        "'[12][0-9][0-9][0-9]*' THEN d.date END AS f FROM mention m JOIN page p USING (pid) "
        "JOIN document d USING (doc_id) WHERE m.ent_id=?) x", (ent_id,)).fetchone()
    n_cand = con.execute("SELECT count(*) FROM mention WHERE ent_id IS NULL AND ' ' || candidates || ' ' LIKE ?",
                         (f"% {ent_id} %",)).fetchone()[0]
    summary = (f"<p class='mut peq'>{n_m:,} mentions in {n_d:,} documents · document dates "
               f"{e(d_min or 'not stated')} to {e(d_max or 'not stated')} · {n_cand:,} ambiguous mentions list it as a candidate"
               + (" · showing the first 1,000" if n_m > 1000 else "") + "</p>")
    dl = "".join(f"<dt>{k}</dt><dd>{e(v)}</dd>" for k, v in zip(
        ["id", "Kind", "Name", "Role", "Notes", "Merged into", "Created by"], en) if v)
    ta = table(["Alias", "Type", "Confidence", "Source"], [[e(a), e(t), e(c), a_pid(s)] for a, t, c, s in aliases])
    tm = table(["Page", "Literal form", "Context", "Status"],
               [[a_page(d, n, pid), e(t), e(qt), e(s)] for pid, d, n, t, qt, s in ment])
    return en[2], f"<h1>{e(en[2])}</h1><dl>{dl}</dl><h2>Aliases ({len(aliases)})</h2>{ta}<h2>Mentions ({n_m:,})</h2>{summary}{tm}"


def extraction(con, q):
    type_, doc = q.get("type", ""), q.get("doc", "")
    page = int(q["page"]) if q.get("page", "").isdigit() and int(q["page"]) > 0 else 1
    if not con.execute("SELECT count(*) FROM extraction").fetchone()[0]:
        return "Extraction", f'<h1>Extracted filings</h1><p class="vacio">No filings yet. They are loaded by {WHO_FILLS["extraction"]}.</p>'
    rows = con.execute(
        "SELECT doc_id, page_start, page_end, folio, type, date, summary, (SELECT group_concat(text, '; ') "
        "FROM extraction_item i WHERE i.ext_id=x.ext_id AND kind='person') FROM extraction x "
        "WHERE (?='' OR type=?) AND (?='' OR doc_id=?) ORDER BY doc_id, page_start LIMIT ? OFFSET ?",
        (type_, type_, doc, doc, 101, (page - 1) * 100)).fetchall()
    types = [(t, t) for t, in con.execute("SELECT DISTINCT type FROM extraction ORDER BY 1")]
    docs_ = [(d, d) for d, in con.execute("SELECT DISTINCT doc_id FROM extraction ORDER BY 1")]
    t = table(["Doc", "Pages", "Folio", "Type", "Date", "Summary", "People"], [
        [e(d), a_page(d, ps, f"{ps}–{pe}" if pe != ps else ps), e(fo), e(tp), e(dt), e(s), e(pp)]
        for d, ps, pe, fo, tp, dt, s, pp in rows[:100]])
    return "Extraction", f"""<h1>Extracted filings</h1><form class="filtros" action="/extraction">
<select name="type" aria-label="Type">{options(types, type_)}</select><select name="doc" aria-label="Document">{options(docs_, doc)}</select>
<button>Filter</button></form>{t}{pager("/extraction", dict(type=type_, doc=doc), page, len(rows) > 100)}"""


def md_header(p):
    # Transcript headers are source material and stay in Spanish (Canal:, Fecha de publicación:, ...).
    meta = {"title": p.stem}
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines()[:12]:
        if line.startswith("# "):
            meta["title"] = line[2:].strip()
        k, _, v = line.partition(":")
        meta[k.strip().lower()] = v.strip()
    return meta


def transcripts(con, q):
    rows = []
    for p in sorted(TRANSCRIPTS.glob("*.md")):
        m = md_header(p)
        rows.append([f'<a href="/transcript/{quote(p.stem)}">{e(m["title"])}</a>', e(m.get("canal")),
                     e(m.get("fecha de publicación")), e(m.get("duración"))])
    body = table(["Title", "Channel", "Published", "Duration"], rows) if rows else \
        '<p class="vacio">No transcripts yet (WP4).</p>'
    return "Transcripts", f"<h1>Transcripts</h1><p class='mut peq'>sources/audiovisual/transcripts/</p>{body}"


def transcript(con, vid):
    p = TRANSCRIPTS / f"{vid}.md"
    if not re.fullmatch(r"[A-Za-z0-9_-]+", vid) or not p.is_file():
        raise NotFound
    m, text = md_header(p), e(p.read_text(encoding="utf-8", errors="replace"))
    yt = m.get("fuente", "")
    if RE_YOUTUBE.match(yt):
        text = link_times(text, yt)
    return m["title"], f'<p class="mut peq"><a href="/transcripts">Transcripts</a></p><h1>{e(m["title"])}</h1><pre class="texto">{text}</pre>'


def source_list(con, q):
    rows = [[f'<a href="/sources/{quote(p.parent.name)}">{e(p.parent.name)}</a>', f"{p.stat().st_size // 1024:,} KB"]
            for p in sorted(SOURCES.glob("*/README.md"))]
    return "Sources", f"<h1>Source indexes</h1>{table(['Folder', 'README.md'], rows)}"


def source_index(con, folder):
    p = SOURCES / folder / "README.md"
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", folder) or folder.startswith(".") or not p.is_file():
        raise NotFound
    paths = dict(con.execute("SELECT original_path, doc_id FROM document")) | dict(
        con.execute("SELECT text_path, doc_id FROM document WHERE text_path IS NOT NULL"))
    root, out, i = SOURCES.resolve(), [], 0
    raw = p.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"\[([^\]\n]+)\]\(([^)\s]+)\)", raw):
        out.append(e(raw[i:m.start()]))
        text, target = m[1], m[2]
        if re.match(r"https?://", target):
            out.append(a_external(target, text))
        else:
            dest = (p.parent / unquote(target.split("#")[0])).resolve()
            rel = "sources/" + str(dest.relative_to(root)) if dest.is_relative_to(root) else None
            if rel in paths:
                out.append(f'<a href="/doc/{quote(paths[rel])}">{e(text)}</a>')
            elif rel and dest.is_file():
                out.append(a_file(rel, text))
            else:
                out.append(e(m[0]))
        i = m.end()
    out.append(e(raw[i:]))
    return f"sources/{folder}", f'<p class="mut peq"><a href="/sources">Sources</a></p><h1>sources/{e(folder)}/README.md</h1><pre class="texto">{"".join(out)}</pre>'


# ---------- server ----------

class NotFound(Exception):
    pass


class Redirect(Exception):
    pass


ROUTES = [(r"/", home), (r"/docs", docs), (r"/search", search_page), (r"/index", index), (r"/entities", entities),
          (r"/extraction", extraction), (r"/transcripts", transcripts), (r"/sources", source_list)]
ID_ROUTES = [(r"/doc/([^/]+)", doc_page), (r"/p/([^/]+)/(\d+)", p_page), (r"/entity/([^/]+)", entity),
             (r"/transcript/([^/]+)", transcript), (r"/sources/([^/]+)", source_index)]


def html_doc(title, body):
    nav = "".join(f'<a href="{r}">{t}</a>' for r, t in NAV[1:])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark"><title>{e(title)}</title><style>{CSS}</style></head><body>
<nav><div><b><a href="/">García Belsunce case</a></b>{nav}<form action="/search"><input name="q" placeholder="Search the corpus" aria-label="Search the corpus" size="22"></form></div></nav>
<main>{body}</main></body></html>""".encode()


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, ctype="text/html; charset=utf-8", extra=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = urlsplit(self.path)
        path = unquote(parts.path)
        q = {k: v[0] for k, v in parse_qs(parts.query).items()}
        if path.startswith("/file/"):
            return self.file(path[len("/file/"):])
        try:
            con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        except sqlite3.OperationalError:
            return self.reply(503, html_doc("No database", '<p class="vacio">Could not open db/case.sqlite. '
                                            'Run <code>python3 tools/build.py</code>.</p>'))
        try:
            for pattern, f in ROUTES:
                if re.fullmatch(pattern, path):
                    return self.reply(200, html_doc(*f(con, q)))
            for pattern, f in ID_ROUTES:
                m = re.fullmatch(pattern, path)
                if m:
                    args = [int(g) if g.isdigit() and i else g for i, g in enumerate(m.groups())]
                    return self.reply(200, html_doc(*f(con, *args)))
            raise NotFound
        except NotFound:
            self.reply(404, html_doc("Not found", '<h1>Not found</h1><p><a href="/">Back to home</a></p>'))
        except Redirect as r:
            self.reply(302, b"", extra=[("Location", str(r))])
        finally:
            con.close()

    def file(self, rel):
        root = SOURCES.resolve()
        p = (root / rel).resolve()
        if not p.is_relative_to(root) or not p.is_file():
            return self.reply(404, html_doc("Not found", '<h1>File not available</h1><p class="vacio">This copy of the '
                                            'corpus does not include it. <a href="/">Back to home</a></p>'))
        ext = p.suffix.lower()
        # Only PDFs and raster images get their own type; everything else (html, md, svg…) is plain text: never executed.
        ctype = mimetypes.guess_type(p.name)[0] if ext in (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp") else "text/plain; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(p.stat().st_size))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        with p.open("rb") as f:
            try:
                shutil.copyfileobj(f, self.wfile)
            except (BrokenPipeError, ConnectionResetError):   # the browser cancelled the download
                pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8766)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"UI at http://127.0.0.1:{a.port}  (Ctrl+C to quit)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
