"""Builds db/case.sqlite from text/ (layer 1) and analysis/ (layer 2).

Usage: python3 tools/build.py [--no-ingest] [--full]
  --no-ingest  does not reread sources/ (uses text/ as it is)
  --full       reprocesses every document in sources/ even if it did not change
The database is written to a temporary file and replaced at the end (readers never see a
half-built database). analysis/extraction/*.jsonl is validated line by line: valid lines go to
extraction/extraction_item/mention; invalid ones go to db/rejected/<file>.jsonl with their error.
"""
import csv
import json
import sqlite3
import sys
import time

import ingest
from common import DB, PAGES, RE_CITATION, ROOT, TEXT, normalize
from extraction import Pages, validate_line

ANALYSIS = ROOT / "analysis"
REJECTED = ROOT / "db" / "rejected"
# Nested fields allowed in layer-2 rows: field -> (table, column pointing to the parent)
NESTED = {("claim", "citations"): ("citation", "claim_id"),
          ("claim", "topics"): ("claim_topic", "claim_id"),
          ("event", "participants"): ("event_participant", "ev_id"),
          ("event", "citations"): ("event_citation", "ev_id"),
          ("statement", "claims"): ("statement_claim", "stmt_id")}
KEY = {"claim": "claim_id", "event": "ev_id", "statement": "stmt_id"}


def columns(con, table):
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})")]


def insert(con, table, row):
    cols = list(row)
    con.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                [row[c] for c in cols])


def load_layer1(con):
    with open(TEXT / "manifest.tsv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            con.execute("INSERT INTO document VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                r["doc_id"], r["type"], r["title"] or None, r["date"] or None, r["original_path"],
                r["text_path"] or None, r["sha256"] or None, r["source_url"] or None,
                r["captured_at"] or None, r["source_level"], int(r["n_pages"]) if r["n_pages"] else None,
                int(r["n_text_pages"]), r["text_status"], r["anchor"]))
    for p in sorted(PAGES.glob("*.jsonl")):
        with open(p, encoding="utf-8") as fh:
            con.executemany(
                "INSERT INTO page (pid, doc_id, n, folio, text, ocr_conf, source_file, line, t_start) VALUES (?,?,?,?,?,?,?,?,?)",
                ((r["pid"], r["doc_id"], r["n"], r["folio"], r["text"], r["ocr_conf"], r["source_file"], r["line"], r.get("t_start"))
                 for r in map(json.loads, fh)))
    with open(TEXT / "filings.tsv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            insert(con, "filing", {k: (v if v != "" else None) for k, v in r.items()})


def load_layer2(con):
    """Each line of analysis/**/*.jsonl (except extraction/) carries "_table" and columns of that table."""
    cols_cache = {}
    for p in sorted(ANALYSIS.rglob("*.jsonl")):
        if "extraction" in p.relative_to(ANALYSIS).parts:
            continue
        for k, line in enumerate(open(p, encoding="utf-8"), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                table = row.pop("_table")
                if table not in cols_cache:
                    cols_cache[table] = columns(con, table)
                    if not cols_cache[table]:
                        raise ValueError(f"unknown table {table!r}")
                children = {c: row.pop(c) for (t, c) in NESTED if t == table and c in row}
                if table == "alias" and not row.get("alias_norm"):
                    row["alias_norm"] = normalize(row.get("alias", ""))
                unknown = set(row) - set(cols_cache[table])
                if unknown:
                    raise ValueError(f"unknown columns in {table}: {sorted(unknown)}")
                insert(con, table, row)
                for field, values in children.items():
                    child, fk = NESTED[(table, field)]
                    for v in values:
                        if child == "claim_topic":
                            v = {"topic_id": v}
                        elif child == "statement_claim":
                            v = {"claim_id": v}
                        insert(con, child, {**v, fk: row[KEY[table]]})
            except (ValueError, KeyError, TypeError, sqlite3.Error) as e:
                con.execute("INSERT INTO load_error VALUES (?,?,?)", (str(p.relative_to(ROOT)), k, str(e)))
    for p in sorted(ANALYSIS.rglob("*.md")):
        source = str(p.relative_to(ROOT))
        for m in RE_CITATION.finditer(p.read_text(encoding="utf-8")):
            con.execute("INSERT INTO link VALUES (?,?)", (source, f"{m.group(1)}#{m.group(2)}{m.group(3)}"))


def load_extraction(con):
    """Validates and ingests analysis/extraction/<doc_id>.jsonl. Returns (valid, rejected)."""
    pages = Pages(con)
    ok = bad = 0
    REJECTED.mkdir(parents=True, exist_ok=True)
    for old in REJECTED.glob("*.jsonl"):
        old.unlink()
    for p in sorted((ANALYSIS / "extraction").glob("*.jsonl")):
        rejected = []
        for k, line in enumerate(open(p, encoding="utf-8"), 1):
            if not line.strip():
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError as e:
                rejected.append({"line": k, "errors": [f"invalid JSON: {e}"], "original": line.strip()})
                continue
            errors = validate_line(pages, o, p.stem)
            if errors:
                rejected.append({"line": k, "errors": errors, "original": o})
                continue
            ext_id, doc = f"{p.stem}:{k}", o["doc_id"]
            ev = o.get("evidence") or {}
            insert(con, "extraction", dict(
                ext_id=ext_id, doc_id=doc, page_start=o["page_start"], page_end=o["page_end"], folio=o.get("folio"),
                type=o["type"], date=(o.get("date") or {}).get("value"), summary=o["summary"],
                evidence_pid=f"{doc}#p{ev['page']}" if ev else None, evidence_quote=ev.get("quote"),
                agent=o.get("agent"), file=str(p.relative_to(ROOT))))
            items = [("date", o["date"])] if o.get("date") else []
            for name, kind in (("people", "person"), ("places", "place"), ("objects", "object"), ("times", "time")):
                items += [(kind, it) for it in o.get(name, [])]
            for kind, it in items:
                pid = f"{doc}#p{it['page']}"
                literal = it.get("text") or it["quote"]
                insert(con, "extraction_item", dict(ext_id=ext_id, kind=kind, text=literal, role=it.get("role"),
                                                    value=it.get("value"), pid=pid, quote=it["quote"]))
                if kind == "person":
                    insert(con, "mention", dict(pid=pid, literal_text=literal, status="auto", quote=it["quote"],
                                                created_by=f"extraction:{ext_id}"))
            ok += 1
        if rejected:
            with open(REJECTED / p.name, "w", encoding="utf-8") as fh:
                for r in rejected:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        bad += len(rejected)
    return ok, bad


def main():
    t0 = time.time()
    if "--no-ingest" not in sys.argv:
        ingest.main(full="--full" in sys.argv)
    tmp = DB.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.executescript((ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
    load_layer1(con)
    load_layer2(con)
    ok, bad = load_extraction(con)
    con.execute("INSERT INTO page_fts(page_fts) VALUES('rebuild')")
    con.execute("INSERT INTO page_tri(page_tri) VALUES('rebuild')")
    con.execute("CREATE TABLE cache_timeline AS SELECT * FROM v_timeline")
    con.execute("""CREATE TABLE cache_comentions AS
        SELECT a.ent_id AS ent_a, b.ent_id AS ent_b, count(DISTINCT a.pid) AS pages
        FROM mention a JOIN mention b ON a.pid = b.pid AND a.ent_id < b.ent_id
        WHERE a.status <> 'rejected' AND b.status <> 'rejected' GROUP BY 1, 2""")
    con.commit()
    con.execute("PRAGMA optimize")
    con.close()
    tmp.replace(DB)
    con = sqlite3.connect(DB)
    summary = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
               for t in ("document", "page", "filing", "entity", "alias", "claim", "citation",
                         "event", "extraction", "extraction_item", "mention", "load_error")}
    print("build:", " ".join(f"{k}={v}" for k, v in summary.items()),
          f"| extraction rejected={bad} (db/rejected/) | {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
