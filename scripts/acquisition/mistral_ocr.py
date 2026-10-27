# usage: mistral_ocr.py <pdf> [<pdf>...] — OCRs each PDF with Mistral, writes <name>.ocr.md and <name>.ocr.json next to it.
import json, os, sys, time, uuid, urllib.request

# MISTRAL_API_KEY from the environment, else from .env.local at the repo root.
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
KEY = os.environ.get("MISTRAL_API_KEY") or dict(l.strip().split("=", 1) for l in open(ROOT / ".env.local") if "=" in l)["MISTRAL_API_KEY"]
API = "https://api.mistral.ai/v1"

def req(method, path, data=None, headers=None, timeout=900):
    h = {"Authorization": f"Bearer {KEY}", **(headers or {})}
    r = urllib.request.Request(API + path, data=data, method=method, headers=h)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.load(resp)

def upload(path):
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"purpose\"\r\n\r\nocr\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(path)}\"\r\n"
            f"Content-Type: application/pdf\r\n\r\n").encode() + open(path, "rb").read() + f"\r\n--{b}--\r\n".encode()
    return req("POST", "/files", body, {"Content-Type": f"multipart/form-data; boundary={b}"})["id"]

for pdf in sys.argv[1:]:
    base = pdf[:-4]
    if os.path.exists(base + ".ocr.md"):
        print("SKIP", pdf); continue
    for attempt in range(8):
        try:
            fid = upload(pdf)
            url = req("GET", f"/files/{fid}/url?expiry=24")["url"]
            out = req("POST", "/ocr", json.dumps({"model": "mistral-ocr-latest",
                      "document": {"type": "document_url", "document_url": url},
                      "table_format": "markdown"}).encode(), {"Content-Type": "application/json"})
            break
        except Exception as e:
            print("RETRY", pdf, attempt, e, flush=True); time.sleep(30 * (attempt + 1))
    else:
        print("FAIL", pdf, flush=True); continue
    json.dump(out, open(base + ".ocr.json", "w"), ensure_ascii=False)
    with open(base + ".ocr.md", "w") as f:
        # "# OCR de" / "## Página N" stay in Spanish: tools/ingest.py parses "## Página N".
        f.write(f"# OCR de {os.path.basename(pdf)}\n\nMotor: Mistral OCR ({out.get('model')}). Cada sección corresponde a una página del PDF.\n")
        for p in out["pages"]:
            f.write(f"\n\n---\n\n## Página {p['index'] + 1}\n\n{p['markdown']}\n")
    try: req("DELETE", f"/files/{fid}")
    except Exception: pass
    print("OK", pdf, len(out["pages"]), "pages", out.get("usage_info"), flush=True)
