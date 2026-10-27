"""Shared utilities: paths, text normalization and citation format."""
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
TEXT = ROOT / "text"
PAGES = TEXT / "pages"
DB = ROOT / "db" / "case.sqlite"

# [[doc#p12]]  [[doc#p12-14]]  [[doc#s3|"literal quote"]]
RE_CITATION = re.compile(r'\[\[([A-Za-z0-9][A-Za-z0-9_.\-]*)#([ps])(\d+)(?:-(\d+))?(?:\|"(.+?)")?\]\]', re.S)
RE_PID = re.compile(r'^([A-Za-z0-9][A-Za-z0-9_.\-]*)#([ps])(\d+)(?:-(\d+))?$')

_HYPHENS = "-¬‐‑"  # hyphen, "¬" and unicode hyphens used to break words


def slug(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def normalize_map(s):
    """Returns (normalized_text, indices) where indices[i] is the position in `s`
    of normalized character i. Normalizes: lowercase, no diacritics, punctuation -> space,
    collapsed spaces, words hyphenated at the end of a line are joined."""
    out, idx = [], []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "­":  # soft hyphen
            i += 1
            continue
        if c in _HYPHENS and i > 0 and s[i - 1].isalnum():
            j = i + 1
            while j < n and s[j] in " \t":
                j += 1
            if j < n and s[j] == "\n":
                j += 1
                while j < n and s[j] in " \t\n|>#":
                    j += 1
                if j < n and s[j].isalnum():
                    i = j
                    continue
        base = unicodedata.normalize("NFKD", c)
        base = "".join(b for b in base if not unicodedata.combining(b)).casefold()
        for b in base:
            if b.isalnum():
                out.append(b)
                idx.append(i)
            elif out and out[-1] != " ":
                out.append(" ")
                idx.append(i)
        i += 1
    while out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


def normalize(s):
    return normalize_map(s)[0]


def find_quote(text, quote):
    """Looks for `quote` in `text` after normalizing. Returns (mode, original_fragment) or (None, None).
    mode = 'exact' or 'ignoring_spaces' (if it only matches when spaces are ignored)."""
    t, idx = normalize_map(text)
    q = normalize(quote)
    if not q:
        return None, None
    k = t.find(q)
    if k >= 0:
        start, end = idx[k], idx[k + len(q) - 1] + 1
        return "exact", " ".join(text[start:end].split())
    if q.replace(" ", "") in t.replace(" ", ""):
        return "ignoring_spaces", None
    return None, None


def open_db(read_only=True):
    if not DB.exists():
        sys.exit(f"{DB} does not exist. Run first: python3 tools/build.py")
    if read_only:
        return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    return sqlite3.connect(DB)


def text_of_pids(con, doc_id, anchor, start, end=None):
    """Concatenated text of pages/sections start..end of a document. None if any is missing."""
    end = end or start
    rows = con.execute(
        "SELECT n, text FROM page WHERE doc_id=? AND pid LIKE ? AND n BETWEEN ? AND ? ORDER BY n",
        (doc_id, f"{doc_id}#{anchor}%", start, end)).fetchall()
    if len(rows) != end - start + 1:
        return None
    return "\n".join(t for _, t in rows)


def verify_citation(con, doc_id, anchor, start, end, quote):
    """Returns (ok, message)."""
    pid = f"{doc_id}#{anchor}{start}" + (f"-{end}" if end else "")
    if end and int(end) < int(start):
        return False, f"{pid}: inverted range"
    text = text_of_pids(con, doc_id, anchor, int(start), int(end) if end else None)
    if text is None:
        doc = con.execute("SELECT text_status, n_pages FROM document WHERE doc_id=?", (doc_id,)).fetchone()
        if not doc:
            return False, f"{pid}: doc_id does not exist"
        return False, f"{pid}: page/section does not exist (text_status={doc[0]}, n_pages={doc[1]})"
    if quote is None:
        return True, f"{pid}: exists"
    mode, _ = find_quote(text, quote)
    if mode == "exact":
        return True, f"{pid}: quote verified"
    if mode == "ignoring_spaces":
        return True, f"{pid}: quote verified ignoring spaces (check OCR breaks)"
    return False, f'{pid}: the quote does not appear on the page: "{quote[:80]}"'
