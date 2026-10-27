"""Merges a document's extraction chunks into analysis/extraction/<doc_id>.jsonl.

  python3 tools/merge_parts.py            # every document with all its chunks present
  python3 tools/merge_parts.py exp-c05    # one

Chunks are defined in work/chunks.tsv (doc_id, page_start, page_end) and written to
analysis/extraction/parts/<doc_id>__p<a>-<b>.jsonl. A document is merged only if all its chunks are present;
then run validate.py on the merged file.
"""
import json
import sys
from collections import defaultdict

from common import ROOT

PARTS = ROOT / "analysis/extraction/parts"


def chunks():
    by_doc = defaultdict(list)
    for line in open(ROOT / "work/chunks.tsv", encoding="utf-8"):
        doc, a, b = line.split()
        by_doc[doc].append((int(a), int(b)))
    return by_doc


def merge(doc, ranges):
    files = [PARTS / f"{doc}__p{a}-{b}.jsonl" for a, b in ranges]
    missing = [f.name for f in files if not f.exists()]
    if missing:
        print(f"{doc}: {len(missing)} chunks missing ({', '.join(missing)})")
        return False
    lines = [json.loads(l) for f in files for l in open(f, encoding="utf-8") if l.strip()]
    lines.sort(key=lambda o: (o.get("page_start") or 0, o.get("page_end") or 0))
    with open(ROOT / f"analysis/extraction/{doc}.jsonl", "w", encoding="utf-8") as out:
        out.writelines(json.dumps(o, ensure_ascii=False) + "\n" for o in lines)
    print(f"{doc}: {len(lines)} filings merged from {len(files)} chunks")
    return True


if __name__ == "__main__":
    everything = chunks()
    for doc in sys.argv[1:] or sorted(everything):
        merge(doc, everything[doc])
