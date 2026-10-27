"""Verifies a citation and prints it in canonical form.

  python3 tools/cite.py exp-c01#p171 "acta entrega de vivienda"
  python3 tools/cite.py exp-c01#p171          # shows the page text
If the quote is not on that page, looks for the pages of the same document where it does appear.
Exits with code 1 if the citation does not verify.
"""
import sys

from common import RE_PID, find_quote, open_db, text_of_pids


def main(args):
    if not args or not RE_PID.match(args[0]):
        print(__doc__)
        return 2
    doc, anchor, start, end = RE_PID.match(args[0]).groups()
    con = open_db()
    text = text_of_pids(con, doc, anchor, int(start), int(end) if end else None)
    if text is None:
        print(f"ERROR: {args[0]} does not exist in the database (misspelled doc_id or number?)")
        return 1
    meta = con.execute("SELECT p.folio, p.source_file, p.line, d.type, d.source_level FROM page p JOIN document d USING (doc_id) "
                       "WHERE p.pid=?", (f"{doc}#{anchor}{start}",)).fetchone()
    folio = f" | detected folio (check against the image): {meta[0]}" if meta[0] else ""
    info = f"{meta[3]}, source {meta[4]} | {meta[1]} line {meta[2]}{folio}"
    if len(args) < 2:   # show each page with its header
        for pid, n, f, t in con.execute(
                "SELECT pid, n, folio, text FROM page WHERE doc_id=? AND pid LIKE ? AND n BETWEEN ? AND ? ORDER BY n",
                (doc, f"{doc}#{anchor}%", int(start), int(end or start))):
            print(f"==== [[{pid}]]" + (f" (detected folio: {f})" if f else "") + f"\n{t}\n")
        print(f"({info})")
        return 0
    mode, literal = find_quote(text, args[1])
    if mode:
        quote = literal or args[1]
        print(f'[[{args[0]}|"{quote}"]]')
        print(f"  verified ({mode}) | {info}")
        return 0
    print(f'ERROR: the quote does not appear in {args[0]}.')
    others = [pid for pid, t in con.execute("SELECT pid, text FROM page WHERE doc_id=? ORDER BY n", (doc,))
              if find_quote(t, args[1])[0]]
    if others:
        print("  It does appear in: " + " ".join(others[:20]))
    else:
        print("  It does not appear on any other page of the document either. Try: python3 tools/search.py \"...\"")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
