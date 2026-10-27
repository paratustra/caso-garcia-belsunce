# usage: blog2md.py <posts.json> <out_dir> — converts the casobelsunce blog posts (JSON dump) into one Markdown
# file per post under <out_dir>/posts/, plus README.md (index) and documentos-enlazados.tsv (linked documents/video).
import json, re, sys, os, html
from html.parser import HTMLParser
src, out = sys.argv[1], sys.argv[2]
posts = json.load(open(src))
os.makedirs(f"{out}/posts", exist_ok=True)

class T(HTMLParser):
    def __init__(s): super().__init__(); s.o=[]; s.links=[]; s.href=None
    def handle_starttag(s, t, a):
        a=dict(a)
        if t in ("br","p","div","li","h1","h2","h3","h4","tr"): s.o.append("\n")
        if t=="a" and a.get("href"): s.href=a["href"]; s.links.append(a["href"])
        if t in ("img","iframe","embed") and a.get("src"): s.links.append(a["src"]); s.o.append(f"\n[{t}: {a['src']}]\n")
    def handle_endtag(s, t):
        if t=="a" and s.href: s.o.append(f" ({s.href})"); s.href=None
    def handle_data(s, d): s.o.append(d)

# Output text stays in Spanish (Spanish corpus); "Fecha:"/"Fuente:" headers are parsed by tools/ingest.py.
doc_re = re.compile(r"\.pdf|\.docx?|drive\.google|docs\.google|scribd|mediafire|archive\.org|dropbox|4shared|issuu|youtube|youtu\.be", re.I)
docs, index = {}, []
for p in sorted(posts, key=lambda x: x["date"]):
    t = T(); t.feed(p["html"])
    body = re.sub(r"\n\s*\n+", "\n\n", html.unescape("".join(t.o))).strip()
    slug = re.sub(r"[^a-z0-9]+", "-", p["title"].lower())[:70].strip("-") or "sin-titulo"
    name = f"{p['date'][:10]}_{slug}.md"
    open(f"{out}/posts/{name}", "w").write(f"# {p['title']}\n\nFecha: {p['date']}\nFuente: {p['url']}\n\n{body}\n")
    index.append(f"- {p['date'][:10]} — [{p['title'] or '(sin título)'}](posts/{name})")
    for l in t.links:
        if doc_re.search(l): docs.setdefault(l, p["url"])
open(f"{out}/README.md","w").write(f"# casobelsunce.blogspot.com — {len(posts)} entradas\n\n" + "\n".join(index) + "\n")
open(f"{out}/documentos-enlazados.tsv","w").write("enlace\tentrada\n" + "\n".join(f"{k}\t{v}" for k,v in docs.items()) + "\n")
print(len(posts), "posts;", len(docs), "links to documents/video")
