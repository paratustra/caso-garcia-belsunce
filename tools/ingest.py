"""Layer 0 -> layer 1: generates text/manifest.tsv, text/pages/<doc_id>.jsonl and text/filings.tsv.

Incremental and idempotent: a document is processed again only if one of its input files changed
(size or modification time). Never writes inside sources/.
Usage: python3 tools/ingest.py [--full]
"""
import csv
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from common import PAGES, ROOT, SOURCES, TEXT, normalize, slug

FIELDS = ["doc_id", "type", "source_level", "title", "date", "source_url", "captured_at",
          "original_path", "text_path", "sha256", "n_pages", "n_text_pages", "text_status",
          "anchor", "signature"]
MAX_SECTION = 3000   # DO NOT CHANGE: the #sN anchors depend on these two values
MIN_SECTION = 800
VIDEO_WINDOW = 300  # DO NOT CHANGE: section #sN of a video is the window [(N-1)*300 s, N*300 s)
RE_TURN = re.compile(r"^\*\*\[(\d+):(\d\d):(\d\d)\] ")
RE_PAGE = re.compile(r"^## Página (\d+)[ \t]*$", re.M)
RE_DATE = re.compile(r"^(\d{4}(?:-\d{2}){0,2})(?=[_-]|$)")


def rel(p):
    return str(p.relative_to(ROOT)) if p else ""


def signature(*paths):
    parts = []
    for p in paths:
        if p and p.exists():
            st = p.stat()
            parts.append(f"{p.name}:{st.st_size}:{st.st_mtime_ns}")
    return "|".join(parts)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def header(text):
    """Title ('# ...') and the 'Fuente:', 'Fecha:', 'Descargado:' metadata from the first lines."""
    meta = {}
    for line in text.splitlines()[:15]:
        if line.startswith("# ") and "title" not in meta:
            meta["title"] = line[2:].strip()
        for key, field in (("Fuente:", "source_url"), ("Descargado:", "captured_at"),
                           ("Fecha:", "date"), ("Fecha de publicación (metadato):", "date")):
            if line.startswith(key) and field not in meta:
                v = line[len(key):].strip()
                if v.startswith("http") or field != "source_url":
                    meta[field] = v[:10] if field == "date" else v
    return meta


def marked_pages(text):
    """Splits a .md with '## Página N' sections. Returns [(n, text, start_line)]."""
    marks = list(RE_PAGE.finditer(text))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end].strip("\n")
        body = re.sub(r"\n+---\s*$", "", body).strip()   # separator between pages
        out.append((int(m.group(1)), body, text.count("\n", 0, m.start()) + 1))
    return out


def sections(text):
    """Splits unpaginated text into stable sections (#sN): cuts at headings once the section
    already has MIN_SECTION characters, and at paragraph boundaries after MAX_SECTION."""
    lines = text.split("\n")
    out, current, start, size = [], [], 1, 0

    def close(nxt):
        nonlocal current, start, size
        body = "\n".join(current).strip()
        if body:
            out.append((len(out) + 1, body, start))
        current, start, size = [], nxt, 0

    for k, line in enumerate(lines, 1):
        if current and ((line.startswith("#") and size >= MIN_SECTION) or
                        (size >= MAX_SECTION and not line.strip())):
            close(k)
        if not current:
            start = k
        current.append(line)
        size += len(line) + 1
    close(len(lines) + 1)
    return out


def ocr_data(json_path):
    """From Mistral's *.ocr.json: ({page_n: confidence}, {page_n: {"tbl-K.md": markdown table}}).
    Confidence is missing if there are no scores; tables replace the [tbl-K.md](tbl-K.md) marker in the .ocr.md."""
    if not json_path or not json_path.exists():
        return {}, {}
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}, {}   # half-written file: retried on the next run
    conf, tables = {}, {}
    for p in data.get("pages", []):
        n = int(p["index"]) + 1
        c = p.get("confidence_scores")
        if isinstance(c, dict):
            c = next((v for k, v in c.items() if "average" in k and isinstance(v, (int, float))), None)
        if isinstance(c, (int, float)):
            conf[n] = round(float(c), 4)
        if p.get("tables"):
            tables[n] = {t["id"]: t["content"].strip() for t in p["tables"]}
    return conf, tables


def with_tables(text, tables):
    """Puts each table in place of its [tbl-K.md](tbl-K.md) marker."""
    for tid, content in tables.items():
        text = text.replace(f"[{tid}]({tid})", content)
    return text


RE_FOLIO = re.compile(r"^\d{1,4}(?:\s*(?:bis|BIS|Bis))?$")


def folio_candidate(text):
    lines = [l.strip().lstrip("#").strip() for l in text.split("\n")
             if l.strip() and not l.lstrip().startswith("![")][:4]
    for l in lines:
        if RE_FOLIO.match(l):
            return l
    return None


def detect_folios(pages):
    """Folio (foja) printed in the top corner: a lone number at the start of the page is accepted
    only if it is consistent with an earlier candidate AND a later one (within <=12 pages): folios
    grow by at most 1 per page. Heuristic: check against the image before citing folios."""
    cand = {}
    for n, text, _ in pages:
        c = folio_candidate(text)
        if c:
            cand[n] = (int(re.match(r"\d+", c).group()), c)
    order = sorted(cand)
    accepted = {}

    def consistent(n1, f1, n2, f2):
        return 0 < f2 - f1 <= n2 - n1

    for i, n in enumerate(order):
        f = cand[n][0]
        before = any(consistent(m, cand[m][0], n, f) for m in order[max(0, i - 6):i] if n - m <= 12)
        after = any(consistent(n, f, m, cand[m][0]) for m in order[i + 1:i + 7] if m - n <= 12)
        if before and after:
            accepted[n] = cand[n][1]
    # conservative second pass: drop those that break the order with their accepted neighbours
    ns = sorted(accepted)
    val = {n: cand[n][0] for n in ns}
    bad = set()
    for i, n in enumerate(ns):
        if i > 0 and not consistent(ns[i - 1], val[ns[i - 1]], n, val[n]):
            bad.update((ns[i - 1], n))
    return {n: v for n, v in accepted.items() if n not in bad}


def splits_by_window(json_path):
    """For each speaker turn (in .md order), list of (window, text) from the word timings of the
    ElevenLabs JSON: a long turn is cut where its words cross a window.
    Reproduces the grouping in scripts/acquisition/transcribe.py (to_md). Reads the raw <id>.json or, in the
    public repo (no raw JSON), its reduced <id>.words.json.gz. [] if there is no readable JSON."""
    try:
        raw = gzip.decompress(json_path.read_bytes()) if json_path.suffix == ".gz" else json_path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, EOFError, gzip.BadGzipFile, json.JSONDecodeError, UnicodeDecodeError):
        return []
    turns, current, speaker, t = [], None, None, 0
    for w in (w for part in data.get("parts", []) for w in part.get("words", [])):
        if w.get("type") != "spacing":
            t = w.get("start") if w.get("start") is not None else t
            spk = w.get("speaker_id") or "?"
            if spk != speaker:
                speaker, current = spk, []
                turns.append(current)
            n = int(t) // VIDEO_WINDOW + 1
            if not current or current[-1][0] != n:
                current.append([n, ""])
        if current is not None:
            current[-1][1] += w["text"]
    return [[(n, x.strip()) for n, x in turn if x.strip()] for turn in turns]


def video_windows(text, json_path=None):
    """Transcript '**[H:MM:SS] speaker_N:** ...' -> fixed windows of VIDEO_WINDOW seconds (#sN =
    [(N-1)*300 s, N*300 s)). A turn goes to the window where it starts; if the JSON gives word timings
    and matches the .md, turns that cross a window are cut there (the continuation goes without a
    header, so a #sN-M range reproduces the paragraph in one piece). Every window up to the last is
    emitted, empty ones included, so #sN always means the same minute.
    Returns [(n, text, line, t_start)]."""
    turns = []   # [window, line, paragraph text]
    for k, line in enumerate(text.split("\n"), 1):
        m = RE_TURN.match(line)
        if m:
            t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
            turns.append([t // VIDEO_WINDOW + 1, k, line])
        elif turns and line.strip():
            turns[-1][2] += "\n" + line
    if not turns:
        return []
    splits = splits_by_window(json_path) if json_path else []
    if len(splits) != len(turns) or any(
            " ".join(" ".join(x for _, x in c).split()) != " ".join(p.split("** ", 1)[-1].split())
            for c, (_, _, p) in zip(splits, turns)):
        splits = [[(n, p)] for n, _, p in turns]   # no JSON or it does not match: whole paragraphs
    else:
        splits = [[(c[0][0], p.split("** ", 1)[0] + "** " + c[0][1])] + c[1:] for c, (_, _, p) in zip(splits, turns)]
    windows = {}
    for c, (_, line, _) in zip(splits, turns):
        for n, x in c:
            windows.setdefault(n, {"line": line, "parts": []})["parts"].append(x)
    return [(n, "\n\n".join(windows[n]["parts"]) if n in windows else "",
             windows[n]["line"] if n in windows else None, (n - 1) * VIDEO_WINDOW)
            for n in range(1, max(windows) + 1)]


# ---------- document discovery ----------

def ocr_folder_doc(folder, doc_id, type_, level):
    """Folder with <name>.pdf, source.json and, once OCR exists, <name>.ocr.md/.ocr.json.
    The public repo ships no PDFs: original_path still names the PDF, and its sha256 stays empty."""
    pdf = next(iter(sorted(folder.glob("*.pdf"))), folder / f"{folder.name}.pdf")
    md = next(iter(sorted(folder.glob("*.ocr.md"))), None)
    js = next(iter(sorted(folder.glob("*.ocr.json"))), None)
    sj = folder / "source.json"
    meta = {}
    if sj.exists():
        try:
            meta = json.loads(sj.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return dict(doc_id=doc_id, type=type_, source_level=level, original=pdf, text=md, conf=js,
                folios=folder.parent.name == "case-file",
                n_pages=meta.get("total") or meta.get("totalSlides") or "",
                title=meta.get("title") or meta.get("cuerpo") or folder.name,
                source_url=meta.get("url") or meta.get("slideshare_url", ""), format="ocr")


def md_doc(path, doc_id, type_, level, original=None):
    return dict(doc_id=doc_id, type=type_, source_level=level, original=original or path, text=path,
                conf=None, folios=False, n_pages="", format="md")


def discover():
    docs = []
    case_file = SOURCES / "case-file"
    for c in sorted(p for p in case_file.iterdir() if p.is_dir()):
        m = re.match(r"Cuerpo-(\d+)([a-z]?)$", c.name)
        doc_id = f"exp-c{m.group(1)}{m.group(2)}" if m else "exp-" + slug(c.name.replace("documentacion-", ""))
        docs.append(ocr_folder_doc(c, doc_id, "case_file", "primary"))
    slide = SOURCES / "slideshare"
    if slide.exists():
        for c in sorted(p for p in slide.iterdir() if p.is_dir()):
            if any(c.glob("*.pdf")) or any(c.glob("*.ocr.md")):
                docs.append(ocr_folder_doc(c, "slide-" + slug(c.name), "case_file", "primary"))
    for f in sorted((SOURCES / "rulings").glob("*.md")):
        if f.name.endswith(".txt.md"):
            stem = f.name[:-7]
            orig = next((p for p in (f.with_name(stem + ".pdf"), f.with_name(stem + ".doc")) if p.exists()), f)
        else:
            stem, orig = f.stem, f
        docs.append(md_doc(f, "fallo-" + slug(stem), "ruling", "primary", orig))
    simple = [("press", "prensa", "press", "secondary"), ("evidence", "evid", "evidence", "secondary"),
              ("testimonies/people", "testim", "testimony", "secondary"),
              ("testimonies", "testim-nota", "press", "secondary"),
              ("blog-casobelsunce/posts", "blog", "blog", "secondary"),
              ("wikipedia", "wiki", "other", "secondary"), ("official", "ofi", "official", "official_derivative")]
    for folder, prefix, type_, level in simple:
        for f in sorted((SOURCES / folder).glob("*.md")):
            if not f.name.upper().startswith(("INDICE", "README")):
                docs.append(md_doc(f, f"{prefix}-{slug(f.stem)}", type_, level))
    for f in sorted((SOURCES / "archive-org").rglob("*.md")):
        if not f.name.upper().startswith(("INDICE", "README")):
            sub = f.parent.name
            docs.append(md_doc(f, f"arch-{slug(sub)}-{slug(f.stem)}", "other", "secondary"))
    for f in sorted((SOURCES / "scribd").glob("*.pdf")):
        d = md_doc(f, "scribd-" + slug(f.stem), "other", "secondary")
        d["format"] = "pdf"
        docs.append(d)
    cat = SOURCES / "audiovisual" / "catalog.csv"
    transcripts = SOURCES / "audiovisual" / "transcripts"
    if cat.exists():
        with open(cat, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                md = transcripts / f"{r['id']}.md"   # without .md (or with .fail) the video has no text
                words = md.with_suffix(".json")
                if not words.exists():
                    words = md.with_suffix(".words.json.gz")
                docs.append(dict(doc_id="vid-" + r["id"], type="video", source_level="secondary",
                                 original=cat, conf=None, words=words, text=md if md.exists() else None, folios=False, n_pages="",
                                 format="video", title=r.get("title", ""), date=r.get("date", ""),
                                 source_url=r.get("url", "")))
    seen = {}
    for d in docs:
        if d["doc_id"] in seen:
            sys.exit(f"duplicate doc_id: {d['doc_id']} ({rel(seen[d['doc_id']])} and {rel(d['original'])})")
        seen[d["doc_id"]] = d["original"]
    return docs


# ---------- extraction ----------

def extract(d):
    """Returns a list of (n, text, line) and the anchor type ('p' or 's')."""
    if not d["text"]:
        return [], "p"
    if d["format"] == "video":
        return video_windows(d["text"].read_text(encoding="utf-8", errors="replace"), d["words"]), "s"
    if d["format"] == "pdf":
        if not shutil.which("pdftotext"):
            return [], "p"
        out = subprocess.run(["pdftotext", "-enc", "UTF-8", str(d["text"]), "-"],
                             capture_output=True, text=True).stdout
        return [(i, t.strip(), None) for i, t in enumerate(out.split("\f"), 1) if i <= out.count("\f")], "p"
    text = d["text"].read_text(encoding="utf-8", errors="replace")
    pages = marked_pages(text)
    if pages:
        return pages, "p"
    return sections(text), "s"


def process(d, prev):
    text_path = d["text"]
    if d["format"] != "video":
        sig = signature(d["original"], text_path, d["conf"])
    else:
        sig = signature(text_path, d["words"]) if text_path else "catalog"
    out = PAGES / f"{d['doc_id']}.jsonl"
    if prev and prev["signature"] == sig and (out.exists() or prev["n_text_pages"] == "0"):
        return prev, False
    pages, anchor = extract(d)
    folios = detect_folios(pages) if d["folios"] else {}   # before the tables: the folio is at the top
    conf, tables = ocr_data(d["conf"])
    if tables and anchor == "p":
        pages = [(n, with_tables(t, tables[n]) if n in tables else t, line) for n, t, line in pages]
    meta = {}
    if d["format"] == "md" and text_path:
        meta = header(text_path.read_text(encoding="utf-8", errors="replace"))
    date = d.get("date") or meta.get("date", "")
    if not date:
        m = RE_DATE.match(Path(str(d["original"])).name)
        date = m.group(1) if m else ""
    if pages:
        tmp = out.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            for n, text, line, *t_start in pages:
                row = {"pid": f"{d['doc_id']}#{anchor}{n}", "doc_id": d["doc_id"], "n": n,
                       "folio": folios.get(n), "ocr_conf": conf.get(n), "source_file": rel(text_path),
                       "line": line, "text": text}
                if t_start:
                    row["t_start"] = t_start[0]
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        tmp.replace(out)
    elif out.exists():
        out.unlink()
    total = d["n_pages"] or (len(pages) if anchor == "p" and pages else "")
    if d["format"] == "video" and not pages:
        status = "pending_transcription"
    elif not pages:
        status = "pending_ocr" if d["format"] == "ocr" else "no_text"
    elif total and anchor == "p" and len(pages) < int(total):
        status = "partial"
    else:
        status = "complete"
    original = d["original"]
    reuse = prev and prev.get("sha256") and prev.get("original_path") == rel(original) \
        and signature(original) in prev["signature"]
    row = dict(doc_id=d["doc_id"], type=d["type"], source_level=d["source_level"],
               title=(d.get("title") or meta.get("title", ""))[:300], date=date,
               source_url=d.get("source_url") or meta.get("source_url", ""),
               captured_at=meta.get("captured_at", ""), original_path=rel(original),
               text_path=rel(text_path), n_pages=total, n_text_pages=len(pages),
               sha256="" if d["format"] == "video" or not original.exists() else (prev["sha256"] if reuse else sha256(original)),
               text_status=status, anchor=anchor, signature=sig)
    return {k: str(v) for k, v in row.items()}, True


# ---------- filings (INDICE-por-cuerpos.tsv) ----------

# keywords match the Spanish subjects (TEMA) of the original index
FILING_TYPES = [("statement", ("declaraci", "testimonial", "indagatoria", "ampliaci")),
                ("expert_report", ("pericia", "peritaje", "informe", "autopsia", "dictamen", "análisis", "analisis")),
                ("record", ("acta",)), ("decision", ("resoluci", "auto ", "decreto", "sentencia", "orden")),
                ("brief", ("escrito", "presentaci", "solicitud", "pedido", "nota", "oficio", "denuncia"))]


def filing_type(subject):
    t = subject.lower()
    for type_, keys in FILING_TYPES:
        if any(t.startswith(c) or f" {c}" in t for c in keys):
            return type_
    return "other"


def build_filings(docs_by_id):
    """One row per index row. 'cuerpo 36' is ambiguous (36a and 36b exist): it is resolved by
    matching the subject against the text of each candidate if there is OCR; otherwise doc_id stays empty."""
    path = SOURCES / "case-file" / "INDICE-por-cuerpos.tsv"
    texts = {}

    def page_text(doc_id, n):
        if doc_id not in texts:
            p = PAGES / f"{doc_id}.jsonl"
            texts[doc_id] = {}
            if p.exists():
                for l in open(p, encoding="utf-8"):
                    r = json.loads(l)
                    texts[doc_id][r["n"]] = r["text"]
        return texts[doc_id].get(n)

    rows = []
    with open(path, encoding="utf-8") as fh:
        for i, r in enumerate(csv.DictReader(fh, delimiter="\t"), 1):
            m = re.match(r"cuerpo\s+(\d+)(?:\s*-\s*([a-z]))?", r["CUERPO"].strip().lower())
            base = f"exp-c{int(m.group(1)):02d}"
            cands = [base + m.group(2)] if m.group(2) else [base]
            if cands[0] not in docs_by_id:
                cands = sorted(k for k in docs_by_id if re.fullmatch(base + "[a-z]", k))
            pm = re.match(r"(\d+)(?:\s*-\s*(\d+))?", r["PAGINA"].strip())
            page, page_end = (int(pm.group(1)), int(pm.group(2)) if pm.group(2) else "") if pm else ("", "")
            doc_id, resol = (cands[0], "direct") if len(cands) == 1 else ("", "ambiguous")
            if len(cands) > 1 and page:
                words = [w for w in normalize(r["TEMA"]).split() if len(w) > 3]
                scores = []
                for c in cands:
                    t = normalize(page_text(c, page) or "")
                    scores.append((sum(w in t for w in words), c))
                scores.sort(reverse=True)
                if scores[0][0] > 0 and (len(scores) == 1 or scores[0][0] > scores[1][0]):
                    doc_id, resol = scores[0][1], "by_text"
            rows.append(dict(filing_id=i, subject=r["TEMA"].strip(), original_volume=r["CUERPO"].strip(),
                             doc_id=doc_id, page=page, page_end=page_end,
                             pid=f"{doc_id}#p{page}" if doc_id and page else "",
                             filing_type=filing_type(r["TEMA"]), doc_resolution=resol,
                             candidates=" ".join(cands)))
    with open(TEXT / "filings.tsv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    return rows


def main(full=False):
    PAGES.mkdir(parents=True, exist_ok=True)
    man = TEXT / "manifest.tsv"
    prevs = {}
    if man.exists() and not full:
        with open(man, encoding="utf-8") as fh:
            prevs = {r["doc_id"]: r for r in csv.DictReader(fh, delimiter="\t")}
    docs = discover()
    rows, changed = [], 0
    for d in docs:
        row, did = process(d, prevs.get(d["doc_id"]))
        rows.append(row)
        changed += did
    ids = {r["doc_id"] for r in rows}
    for p in PAGES.glob("*.jsonl"):   # documents that no longer exist in sources/
        if p.stem not in ids:
            p.unlink()
    tmp = man.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(man)
    filings = build_filings({r["doc_id"]: r for r in rows})
    print(f"ingest: {len(rows)} documents ({changed} processed again), {len(filings)} filings")
    return rows


if __name__ == "__main__":
    main(full="--full" in sys.argv)
