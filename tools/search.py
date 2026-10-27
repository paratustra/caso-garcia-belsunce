"""Full-text search with snippets and ready-to-paste citations.

  python3 tools/search.py "pozo ciego"              # exact phrase, ignoring accents/case
  python3 tools/search.py CAZAFUS --variants        # includes close spelling variants
  python3 tools/search.py --sub zafus               # substring (trigrams, >= 3 letters)
  python3 tools/search.py --fts 'NEAR(ambulancia llamado, 8)'   # raw FTS5 syntax
Filters: --doc exp-c05 (doc_id prefix, e.g. exp- or fallo-), --type case_file, --limit 20
If the exact search returns nothing, variants and then substrings are tried automatically.
The printed citations are literal fragments of the page: they pass validate.py as they are.
"""
import argparse
import difflib
import sys

from common import normalize, open_db


def variants(con, word, n=8):
    """Index terms similar to `word` (edit distance), with their frequency."""
    w = normalize(word).replace(" ", "")
    if len(w) < 4:
        return []
    terms = dict(con.execute("SELECT term, cnt FROM page_vocab WHERE length(term) BETWEEN ? AND ?",
                             (len(w) - 2, len(w) + 2)))
    close = difflib.get_close_matches(w, terms, n=n, cutoff=0.75)
    return [(t, terms[t]) for t in close]


def query(con, table, expr, a, marks=("«", "»")):
    filt, params = "", [expr]
    if a.doc:
        filt += " AND p.doc_id LIKE ?"
        params.append(a.doc + "%")
    if a.type:
        filt += " AND d.type = ?"
        params.append(a.type)
    n1, n2 = (64, 48) if table == "page_tri" else (24, 14)   # with trigrams each token is ~1 letter
    by_type = con.execute(f"SELECT d.type, count(*) FROM {table} JOIN page p ON p.rowid = {table}.rowid "
                          f"JOIN document d USING (doc_id) WHERE {table} MATCH ?{filt} GROUP BY 1 ORDER BY 2 DESC", params).fetchall()
    total = sum(c for _, c in by_type)
    rows = con.execute(
        f"SELECT p.pid, p.folio, d.type, snippet({table}, 0, ?, ?, ' … ', {n1}), snippet({table}, 0, '', '', '', {n2}) "
        f"FROM {table} JOIN page p ON p.rowid = {table}.rowid JOIN document d USING (doc_id) "
        f"WHERE {table} MATCH ?{filt} ORDER BY d.source_level <> 'primary', rank LIMIT ?", list(marks) + params + [a.limit]).fetchall()
    return total, rows, by_type


def fts_phrase(text):
    return '"' + " ".join(normalize(text).split()) + '"'


def search(con, q, a, marks=("«", "»")):
    """Picks the mode like the command line does (phrase -> variants -> substring).
    `a` needs: fts, sub, variants, doc, type, limit.
    Returns (mode, expr, total, rows, by_type, variants_by_word)."""
    words = normalize(q).split()
    vars_ = {}
    if not a.fts and not a.sub and len(words) <= 3:
        for w in (w for w in words if len(w) >= 5):
            vs = variants(con, w)
            if [t for t, _ in vs if t != w]:
                vars_[w] = vs

    if a.sub:
        mode, table, expr = "substring", "page_tri", fts_phrase(q)
    elif a.fts:
        mode, table, expr = "fts", "page_fts", q
    else:
        mode, table, expr = "phrase", "page_fts", fts_phrase(q)
    total, rows, by_type = query(con, table, expr, a, marks)

    def variants_expr():
        parts = []
        for w in words:
            options = {w} | {t for t, _ in vars_.get(w, [])}
            parts.append("(" + " OR ".join(f'"{o}"' for o in sorted(options)) + ")")
        return " AND ".join(parts)

    if (a.variants or total == 0) and vars_ and mode == "phrase":
        mode, expr = "variants", variants_expr()
        total, rows, by_type = query(con, "page_fts", expr, a, marks)
    if total == 0 and mode != "substring" and not a.fts and len(normalize(q)) >= 3:
        mode, table, expr = "substring", "page_tri", fts_phrase(q)
        total, rows, by_type = query(con, table, expr, a, marks)
    return mode, expr, total, rows, by_type, vars_


def citation(pid, lit, mode):
    """Ready-to-paste citation built from the literal fragment without marks."""
    if mode == "substring":   # the trigram fragment cuts words at both ends
        lit = " ".join(lit.split()[1:-1])
    return f"[[{pid}|\"{' '.join(lit.replace('"', "'").split())}\"]]"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="+")
    ap.add_argument("--fts", action="store_true", help="the query is FTS5 syntax")
    ap.add_argument("--sub", action="store_true", help="substring search (trigrams)")
    ap.add_argument("--variants", action="store_true", help="adds close spelling variants")
    ap.add_argument("--doc"), ap.add_argument("--type")
    ap.add_argument("--limit", type=int, default=10)
    a = ap.parse_args()
    q = " ".join(a.query)
    con = open_db()
    mode, expr, total, rows, by_type, vars_ = search(con, q, a)

    print(f"query: {q!r} | mode: {mode} | FTS expression: {expr} | {total} pages: "
          + ", ".join(f"{t} {c}" for t, c in by_type) + " (primary sources first)")
    for w, vs in vars_.items():
        print(f"  variants of {w!r} in the corpus: " + ", ".join(f"{t} ({c} pp.)" for t, c in vs))
    for pid, folio, type_, snip, lit in rows:
        f = f" fs.{folio}?" if folio else ""
        print(f"\n{pid}{f} [{type_}]\n  {' '.join(snip.split())}\n  citation: {citation(pid, lit, mode)}")
    if total > len(rows):
        print(f"\n… {total - len(rows)} more (use --limit, --doc or --type)")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
