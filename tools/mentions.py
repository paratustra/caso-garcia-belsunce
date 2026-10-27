"""WP7: deterministic mention sweep. Looks for every alias of every current entity on every layer-1 page
and writes analysis/mentions/<doc_id>.jsonl (_table=mention, created_by=WP7/mentions.py).

  python3 tools/mentions.py            # sweeps everything (idempotent: only rewrites what changes)
  python3 tools/mentions.py --sample 50   # also prints a deterministic sample to review by eye

Inputs: entities and aliases as they are in db/case.sqlite (run build.py first if they changed) and
text/pages/*.jsonl. Rules (see DECISIONES.md, "Barrido de menciones"):
  - same normalization as citations (common.normalize_map); whole words; the longest alias wins;
  - an alias in several entities or of type possible_homonym is not linked: ent_id NULL, status 'doubtful',
    candidates = space-separated ent_ids;
  - alias written with an initial capital: the form in the text must also start with a capital;
  - one-word alias written all lowercase (common noun: "dormitorio") is not swept, except nicknames;
  - one-word alias shorter than 4 characters is not swept;
  - a person's nickname or bare first name ("Dino", "Betty", "Fayt"): only if the entity's surname
    (first token of the ent_id) appears on the same page.
"""
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict

from common import PAGES, ROOT, normalize, normalize_map, open_db

OUT = ROOT / "analysis" / "mentions"
REPORT = ROOT / "work" / "review" / "WP7"
AUTHOR = "WP7/mentions.py"
WINDOW = 6  # context words on each side in `quote`
RE_BREAK = re.compile(r"(\w)[-¬‐‑]\s*\n[\s|>#]*(\w)")
SAFE_QUOTE = str.maketrans({'"': "'", "|": " ", "[": "(", "]": ")"})


def load_aliases(con):
    """Returns ({tokens: rule}, excluded); rule = dict(ents, ambiguous, upper, support)."""
    rows = con.execute("""SELECT a.alias, a.type, v.current, e.kind FROM alias a
        JOIN entity_current v ON v.ent_id = a.ent_id JOIN entity e ON e.ent_id = v.current""").fetchall()
    rows += con.execute("SELECT canonical_name, 'canonical', ent_id, kind FROM entity WHERE merged_into IS NULL").fetchall()
    groups = defaultdict(list)
    for alias, type_, ent, kind in rows:
        groups[tuple(normalize(alias).split())].append((alias, type_, ent, kind))
    rules, excluded = {}, []
    for toks, fs in groups.items():
        if not toks:
            continue
        ents = sorted({f[2] for f in fs})
        types = {f[1] for f in fs}
        letters = [next((c for c in f[0] if c.isalpha()), "") for f in fs]
        single = len(toks) == 1 and not toks[0].isdigit()
        if single and len(toks[0]) < 4:
            excluded.append((toks, "fewer than 4 characters"))
            continue
        forms = [f[0] for f in fs if f[1] != "canonical"] or [f[0] for f in fs]
        if single and "nickname" not in types and not any(c.isupper() for f in forms for c in f):
            excluded.append((toks, "lowercase common word"))
            continue
        ambiguous = len(ents) > 1 or "possible_homonym" in types
        support = None
        if single and fs[0][3] == "person":
            surnames = {e.split(":", 1)[1].split("-")[0] for e in ents}
            bare_name = ambiguous and not any(t[:4] == toks[0][:4] for e in ents for t in e.split(":", 1)[1].split("-"))
            if "nickname" in types or bare_name:
                support = surnames - {toks[0]}
        rules[toks] = dict(ents=ents, ambiguous=ambiguous, upper=all(c.isupper() for c in letters if c),
                           support=support)
    return rules, excluded


def context(text, a, b):
    left = text[max(0, a - 200):a]
    right = text[b:b + 200]
    pl = RE_BREAK.sub(r"\1\2", left).split()
    if a > 200 and pl and not left[0].isspace():
        pl = pl[1:]
    pr = RE_BREAK.sub(r"\1\2", right).split()
    if b + 200 < len(text) and pr and not right[-1].isspace():
        pr = pr[:-1]
    center = RE_BREAK.sub(r"\1\2", text[a:b])
    return " ".join(pl[-WINDOW:] + center.split() + pr[:WINDOW]).translate(SAFE_QUOTE)


def sweep_page(pid, text, rules, firsts):
    norm, idx = normalize_map(text)
    toks = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", norm)]
    words = {t for _, _, t in toks}
    rows, seen, i = [], set(), 0
    while i < len(toks):
        found = None
        for k in firsts.get(toks[i][2], ()):
            cand = tuple(t for _, _, t in toks[i:i + k])
            if len(cand) == k and cand in rules:
                found = (k, cand)
                break
        if not found:
            i += 1
            continue
        k, cand = found
        r = rules[cand]
        a, b = idx[toks[i][0]], idx[toks[i + k - 1][1] - 1] + 1
        i += k
        if r["upper"] and not text[a].isupper():
            continue
        if r["support"] is not None and not (r["support"] & words):
            continue
        key = (" ".join(r["ents"]), cand)
        if key in seen:
            continue
        seen.add(key)
        quote = context(text, a, b)
        literal = " ".join(text[a:b].split())
        if f" {normalize(quote)} " not in f" {norm} ":
            quote = literal
        row = {"_table": "mention", "pid": pid, "ent_id": None if r["ambiguous"] else r["ents"][0],
               "literal_text": literal, "status": "doubtful" if r["ambiguous"] else "auto",
               "candidates": " ".join(r["ents"]) if r["ambiguous"] else None, "quote": quote, "created_by": AUTHOR}
        rows.append(row)
    return rows


def write(path, lines):
    content = "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return True


def proposals(con, rules):
    """Person surnames that are not one-word aliases, with pages in the corpus (for WP5)."""
    singles = {t[0] for t in rules if len(t) == 1}
    vocab = dict(con.execute("SELECT term, doc FROM page_vocab WHERE length(term) >= 4"))
    by_surname = defaultdict(list)
    for ent, in con.execute("SELECT ent_id FROM entity WHERE kind='person' AND merged_into IS NULL ORDER BY 1"):
        by_surname[ent.split(":", 1)[1].split("-")[0]].append(ent)
    rows = [(s, vocab[s], " ".join(ents)) for s, ents in by_surname.items() if s not in singles and vocab.get(s)]
    rows.sort(key=lambda f: -f[1])
    with open(REPORT / "proposed-aliases.tsv", "w", encoding="utf-8") as fh:
        fh.write("surname\tcorpus_pages\tentities_with_that_surname\n")
        for f in rows:
            fh.write("\t".join(map(str, f)) + "\n")
    return len(rows)


def main(args):
    t0 = time.time()
    con = open_db()
    rules, excluded = load_aliases(con)
    firsts = defaultdict(list)
    for toks in rules:
        firsts[toks[0]].append(len(toks))
    for k in firsts:
        firsts[k] = sorted(set(firsts[k]), reverse=True)
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    written, changed, total, every = set(), 0, Counter(), []
    for p in sorted(PAGES.glob("*.jsonl")):
        rows = []
        with open(p, encoding="utf-8") as fh:
            for r in map(json.loads, fh):
                rows += sweep_page(r["pid"], r["text"], rules, firsts)
        if not rows:
            continue
        path = OUT / p.name
        written.add(path.name)
        changed += write(path, rows)
        for f in rows:
            total[f["status"]] += 1
        every += rows
    deleted = 0
    for old in OUT.glob("*.jsonl"):
        if old.name not in written:
            old.unlink()
            deleted += 1
    n_prop = proposals(con, rules)
    print(f"mentions: {sum(total.values())} ({dict(total)}) in {len(written)} documents | "
          f"files changed={changed} deleted={deleted} | aliases swept={len(rules)} "
          f"excluded={len(excluded)} ({', '.join(' '.join(t) + ': ' + m for t, m in excluded)}) | "
          f"surnames proposed={n_prop} (work/review/WP7/proposed-aliases.tsv) | {time.time() - t0:.1f}s")
    if args[:1] == ["--sample"]:
        rnd = random.Random(int(hashlib.sha256(b"WP7").hexdigest(), 16))
        for f in rnd.sample(every, int(args[1])):
            print(f'{f["pid"]}\t{f["ent_id"] or "?" + f["candidates"]}\t{f["literal_text"]}\t{f["quote"]}')


if __name__ == "__main__":
    main(sys.argv[1:])
