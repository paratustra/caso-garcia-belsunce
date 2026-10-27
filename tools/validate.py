"""Validates citations and consistency. Exits with code 1 if there are errors.

  python3 tools/validate.py                      # everything: built database + analysis/ + work/review/
  python3 tools/validate.py FILE [FILE...]       # only those files (.md/.jsonl; EXT extraction included)
  python3 tools/validate.py --citation '[[exp-c01#p171|"ACTA ENTREGA DE VIVIENDA"]]'
  python3 tools/validate.py --sample 5 analysis/extraction/exp-c01.jsonl   # sample for auditing
"""
import hashlib
import json
import random
import re
import sys
from pathlib import Path

from common import RE_CITATION, ROOT, open_db, verify_citation
from extraction import Pages, coverage, ranges, validate_line

RE_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2})?)?)?)?$")


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def citations_in_text(con, text, where):
    errors = []
    for m in RE_CITATION.finditer(text):
        ok, msg = verify_citation(con, *m.groups())
        if not ok:
            errors.append(f"{where}: {msg}")
    return errors


def validate_extraction(con, path, chunk=None):
    """chunk=(a, b): partial file analysis/extraction/parts/<doc>__p<a>-<b>.jsonl; coverage is required only in a..b."""
    pages, errors, valid = Pages(con), [], []
    doc = path.stem.split("__")[0]
    for k, line in enumerate(open(path, encoding="utf-8"), 1):
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}:{k}: invalid JSON ({e})")
            continue
        es = validate_line(pages, o, doc)
        errors += [f"{path.name}:{k}: {x}" for x in es]
        if not es:
            valid.append(o)
    row = con.execute("SELECT n_text_pages FROM document WHERE doc_id=?", (doc,)).fetchone()
    if not row:
        return errors + [f"{path.name}: the file name must be <doc_id>.jsonl of an existing document"]
    missing, doubles = coverage(valid, row[0])
    if chunk:
        a, b = chunk
        outside = [o for o in valid if o["page_start"] < a or o["page_end"] > b]
        errors += [f"{path.name}: filing {o['page_start']}-{o['page_end']} outside chunk {a}-{b}" for o in outside]
        missing = [p for p in missing if a <= p <= b]
        doubles = [p for p in doubles if a <= p <= b]
    if missing:
        errors.append(f"{path.name}: pages without a valid filing: {ranges(missing)}")
    if doubles:
        errors.append(f"{path.name}: pages covered by more than one filing: {ranges(doubles)}")
    total = chunk[1] - chunk[0] + 1 if chunk else row[0]
    print(f"{path.name}: {len(valid)} valid filings, {total - len(missing)}/{total} pages covered")
    return errors


def validate_file(con, path):
    if path.suffix == ".jsonl" and path.parent.name == "extraction":
        return validate_extraction(con, path)
    if path.suffix == ".jsonl" and path.parent.name == "parts":
        m = re.fullmatch(r"(.+)__p(\d+)-(\d+)", path.stem)
        if not m:
            return [f"{path.name}: the name must be <doc_id>__p<a>-<b>.jsonl"]
        return validate_extraction(con, path, (int(m[2]), int(m[3])))
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".jsonl":
        return citations_in_text(con, text, str(path))
    errors = []
    for k, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"{path}:{k}: invalid JSON ({e})")
            continue
        for s in strings(o):
            errors += citations_in_text(con, s, f"{path}:{k}")
    return errors


def validate_db(con):
    e = []
    q = lambda sql: con.execute(sql).fetchall()
    e += [f"{f}:{l}: could not be loaded: {m}" for f, l, m in q("SELECT * FROM load_error")]
    for claim, pid, quote in q("SELECT claim_id, pid, quote FROM citation UNION ALL SELECT ev_id, pid, quote FROM event_citation"):
        m = re.match(r"^(.+)#([ps])(\d+)(?:-(\d+))?$", pid or "")
        ok, msg = verify_citation(con, *m.groups(), quote) if m else (False, f"malformed pid {pid!r}")
        if not ok:
            e.append(f"citation of {claim}: {msg}")
    e += [f"claim without citation: {c} ({t[:60]})" for c, t, _ in q("SELECT * FROM v_uncited")]
    e += [f"event without citation: {v}" for (v,) in q("SELECT ev_id FROM event e WHERE NOT EXISTS (SELECT 1 FROM claim a JOIN citation c USING (claim_id) WHERE a.ev_id = e.ev_id) AND NOT EXISTS (SELECT 1 FROM event_citation x WHERE x.ev_id = e.ev_id)")]
    for table, col in (("event", "t_start"), ("event", "t_end"), ("claim", "stated_at"), ("statement", "date")):
        e += [f"{table}.{col} malformed: {v!r}" for (v,) in q(f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL") if not RE_DATE.match(v)]
    e += [f"alias_norm in several entities (use type possible_homonym if appropriate): {a} -> {s}" for a, s in q("SELECT * FROM v_ambiguous_aliases")]
    e += [f"cycle or broken chain in merged_into: {x}" for (x,) in q("SELECT ent_id FROM entity WHERE ent_id NOT IN (SELECT ent_id FROM entity_current)")]
    e += [f"broken foreign key: {t} row {r} -> {p}" for t, r, p, _ in q("PRAGMA foreign_key_check")
          if t not in ("filing",)]
    e += [f"filing {i} points outside the document: {pid}" for i, pid in q(
        "SELECT filing_id, pid FROM filing x JOIN document d USING (doc_id) WHERE x.page > d.n_pages")]
    for p in sorted((ROOT / "db" / "rejected").glob("*.jsonl")):
        n = sum(1 for _ in open(p, encoding="utf-8"))
        e.append(f"{p.relative_to(ROOT)}: {n} extraction lines rejected by build.py")
    return e


def sample(path, pct):
    """Deterministic sample (seed = file name) of pct % of the lines, at least 3."""
    lines = [(k, l) for k, l in enumerate(open(path, encoding="utf-8"), 1) if l.strip()]
    n = min(len(lines), max(3, round(len(lines) * pct / 100)))
    rnd = random.Random(int(hashlib.sha256(path.name.encode()).hexdigest(), 16))
    for k, l in sorted(rnd.sample(lines, n)):
        print(f"--- line {k}\n{l.rstrip()}")


def main(args):
    con = open_db()
    if args[:1] == ["--sample"]:
        sample(Path(args[2]), float(args[1]))
        return 0
    if args[:1] == ["--citation"]:
        errors = []
        for c in args[1:]:
            if not RE_CITATION.fullmatch(c.strip()):
                errors.append(f"invalid format: {c}")
            errors += citations_in_text(con, c, "citation")
        if not errors:
            print("OK")
    elif args:
        errors = []
        for a in args:
            p = Path(a)
            for f in sorted(p.rglob("*")) if p.is_dir() else [p]:
                if f.suffix in (".md", ".jsonl"):
                    errors += validate_file(con, f)
    else:
        errors = validate_db(con)
        for folder in ("analysis", "work/review"):
            for f in sorted((ROOT / folder).rglob("*")):
                if f.suffix in (".md", ".jsonl") and f.name != "README.md":
                    errors += validate_file(con, f) if not (f.parent.name == "extraction" and folder == "analysis") else []
    for x in errors:
        print("ERROR", x)
    print(f"validate: {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
