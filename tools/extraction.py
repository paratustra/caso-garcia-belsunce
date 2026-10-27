"""Validation of the lines of analysis/extraction/<doc_id>.jsonl (EXT-* tasks).

Closed schema of a line (one filing = one document inside the volume, 1..N consecutive pages):
{"doc_id": "exp-c01", "page_start": 171, "page_end": 171, "folio": null | "120",
 "type": <TYPES>, "date": null | {"value": "YYYY-MM-DD", "page": 171, "quote": "..."},
 "summary": "one line", "evidence": {"page": 171, "quote": "..."} | null (only if every page is near empty),
 "people": [{"text": "literal form", "role": null | "...", "page": 171, "quote": "..."}],
 "places": [{"text", "page", "quote"}], "objects": [{"text", "page", "quote"}],
 "times": [{"value": "HH:MM", "page", "quote"}], "agent": "name-or-model"}
Rules: each 'quote' appears on page 'page' (normalizing accents/spaces/hyphens);
'text' is inside its 'quote'; 'page' is within page_start..page_end.
"""
import re

from common import find_quote, normalize

TYPES = ("witness_statement", "defendant_statement", "expert_report", "report", "record", "official_letter",
         "decision", "party_brief", "log_sheet", "photo_sketch", "other")
KEYS = {"doc_id", "page_start", "page_end", "folio", "type", "date", "summary", "evidence",
        "people", "places", "objects", "times", "agent"}
LISTS = {"people": ("text", "role"), "places": ("text",), "objects": ("text",), "times": ("value",)}
RE_ISO = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
RE_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MAX_QUOTE = 300
NEAR_EMPTY = 30   # normalized characters: below this, the page counts as blank


class Pages:
    """Cache of a document's texts read from the database (page table)."""
    def __init__(self, con):
        self.con, self.cache = con, {}

    def text(self, doc_id, n):
        if doc_id not in self.cache:
            self.cache[doc_id] = dict(self.con.execute(
                "SELECT n, text FROM page WHERE doc_id=? AND pid LIKE ?", (doc_id, doc_id + "#p%")))
        return self.cache[doc_id].get(n)


def _cite(pages, doc_id, start, end, obj, where, errors, text_inside=None):
    if not isinstance(obj, dict):
        errors.append(f"{where}: must be an object with page and quote")
        return
    page, quote = obj.get("page"), obj.get("quote")
    if not isinstance(page, int) or not (start <= page <= end):
        errors.append(f"{where}: page={page!r} outside {start}..{end}")
        return
    if not isinstance(quote, str) or len(normalize(quote)) < 3:
        errors.append(f"{where}: missing literal quote")
        return
    if len(quote) > MAX_QUOTE:
        errors.append(f"{where}: quote longer than {MAX_QUOTE} characters; cite a short fragment")
    text = pages.text(doc_id, page)
    if text is None:
        errors.append(f"{where}: page {doc_id}#p{page} does not exist")
        return
    mode, _ = find_quote(text, quote)
    if not mode:
        errors.append(f'{where}: the quote is not on {doc_id}#p{page}: "{quote[:70]}"')
    if text_inside is not None and normalize(text_inside) not in normalize(quote):
        errors.append(f'{where}: "{text_inside}" is not inside its quote')


def validate_line(pages, obj, expected_doc=None):
    """Returns the list of errors (empty = valid line)."""
    if not isinstance(obj, dict):
        return ["the line is not a JSON object"]
    e = []
    extra = set(obj) - KEYS
    if extra:
        e.append(f"keys not allowed: {sorted(extra)}")
    doc_id = obj.get("doc_id")
    if expected_doc and doc_id != expected_doc:
        e.append(f"doc_id {doc_id!r} differs from the file ({expected_doc})")
    start, end = obj.get("page_start"), obj.get("page_end")
    if not (isinstance(start, int) and isinstance(end, int) and 1 <= start <= end):
        return e + ["page_start/page_end must be integers with 1 <= page_start <= page_end"]
    if pages.text(doc_id, end) is None or pages.text(doc_id, start) is None:
        return e + [f"pages {start}..{end} do not exist in {doc_id}"]
    if obj.get("type") not in TYPES:
        e.append(f"type {obj.get('type')!r} is not in {TYPES}")
    if obj.get("folio") is not None and not isinstance(obj["folio"], str):
        e.append("folio must be text or null")
    s = obj.get("summary")
    if not isinstance(s, str) or not s.strip() or "\n" in s or len(s) > 300:
        e.append("summary: a single line, 1-300 characters")
    if obj.get("evidence") is None and all(
            len(normalize(pages.text(doc_id, n) or "")) < NEAR_EMPTY for n in range(start, end + 1)):
        pass   # blank or image-only pages: there is no quote to cite
    else:
        _cite(pages, doc_id, start, end, obj.get("evidence"), "evidence", e)
    d = obj.get("date")
    if d is not None:
        if not isinstance(d, dict) or not RE_ISO.match(str(d.get("value", ""))):
            e.append("date: null or {value: YYYY-MM-DD, page, quote}")
        else:
            _cite(pages, doc_id, start, end, d, "date", e)
    for name, fields in LISTS.items():
        items = obj.get(name, [])
        if not isinstance(items, list):
            e.append(f"{name} must be a list")
            continue
        for k, it in enumerate(items):
            where = f"{name}[{k}]"
            if not isinstance(it, dict) or set(it) - set(fields) - {"page", "quote"}:
                e.append(f"{where}: allowed keys {fields + ('page', 'quote')}")
                continue
            if name == "times":
                if not RE_TIME.match(str(it.get("value", ""))):
                    e.append(f"{where}: value must be HH:MM")
                _cite(pages, doc_id, start, end, it, where, e)
            else:
                if not isinstance(it.get("text"), str) or not it["text"].strip():
                    e.append(f"{where}: missing text")
                    continue
                _cite(pages, doc_id, start, end, it, where, e, text_inside=it["text"])
    return e


def coverage(valid_lines, n_pages):
    """Pages 1..n_pages not covered by any valid filing, and pages covered twice."""
    count = [0] * (n_pages + 1)
    for o in valid_lines:
        for p in range(o["page_start"], min(o["page_end"], n_pages) + 1):
            count[p] += 1
    missing = [p for p in range(1, n_pages + 1) if count[p] == 0]
    doubles = [p for p in range(1, n_pages + 1) if count[p] > 1]
    return missing, doubles


def ranges(nums):
    out, start = [], None
    for i, n in enumerate(nums):
        if start is None:
            start = n
        if i + 1 == len(nums) or nums[i + 1] != n + 1:
            out.append(f"{start}-{n}" if n != start else str(n))
            start = None
    return ",".join(out)
