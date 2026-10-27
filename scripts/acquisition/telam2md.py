# usage: telam2md.py <html> <url> <ts> — prints Markdown of an archived Télam article (title, subheading (bajada), body);
# <ts> is the Wayback Machine timestamp of the copy. Output headers stay in Spanish (Spanish corpus).
import sys, re, html
h = open(sys.argv[1], 'rb').read().decode('utf-8', 'replace'); u, ts = sys.argv[2], sys.argv[3]
def txt(s): return re.sub(r'\n\s*\n+', '\n\n', html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'<br\s*/?>|</p>|</h\d>', '\n\n', s)))).strip()
t = re.search(r'<title>(.*?)</title>', h, re.S); t = html.unescape(t.group(1).strip()) if t else ''
head = re.search(r'class="head-content[^"]*"[^>]*>(.*?)</div>\s*</div>', h, re.S)
body = re.search(r'class="wrapper-editable-content"[^>]*>(.*?)<div class="(?:tags|share|related)', h, re.S) or re.search(r'class="wrapper-editable-content"[^>]*>(.*)', h, re.S)
b = txt(re.sub(r'<script.*?</script>|<style.*?</style>', '', body.group(1), flags=re.S)) if body else ''
print(f"# {t}\n\nFuente: {u}\nCopia archivada: https://web.archive.org/web/{ts}/{u}\n\n{txt(head.group(1)) if head else ''}\n\n{b[:60000]}")
