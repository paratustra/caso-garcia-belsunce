# usage: transcribe.py <audio>... — transcribes each audio with ElevenLabs Scribe v2 (Spanish, diarization,
# case keyterms) into sources/audiovisual/transcripts/<id>.json (raw) and <id>.md (readable, timestamped).
# Audio longer than CHUNK seconds is split with ffmpeg and timestamps are re-offset.
# Also writes <id>.words.json.gz: only the word fields tools/ingest.py needs, small enough to publish.
#   transcribe.py --words <id.json>...   rebuilds <id>.words.json.gz from existing raw JSON files
import gzip, json, os, subprocess, sys, tempfile, time, uuid, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "sources/audiovisual/transcripts"
# ELEVENLABS_API_KEY from the environment, else from .env.local at the repo root.
def api_key():
    return os.environ.get("ELEVENLABS_API_KEY") or dict(l.strip().split("=", 1) for l in open(ROOT / ".env.local") if "=" in l)["ELEVENLABS_API_KEY"]
KEYTERMS = [t.strip() for t in open(ROOT / "sources/audiovisual/keyterms.txt") if t.strip()]
CHUNK = 2 * 3600

def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())

def scribe(path):
    b = uuid.uuid4().hex
    fields = [("model_id", "scribe_v2"), ("language_code", "spa"), ("diarize", "true"),
              ("tag_audio_events", "true"), ("timestamps_granularity", "word")] + [("keyterms", k) for k in KEYTERMS]
    body = b"".join(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode() for k, v in fields)
    body += (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(path)}\"\r\n"
             f"Content-Type: application/octet-stream\r\n\r\n").encode() + open(path, "rb").read() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=body, method="POST",
                                 headers={"xi-api-key": api_key(), "Content-Type": f"multipart/form-data; boundary={b}"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=3600) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:300]
            if e.code in (429, 500, 502, 503, 504):
                print("RETRY", path, e.code, msg, flush=True); time.sleep(30 * (attempt + 1)); continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")
    raise RuntimeError("too many retries")

def write_words(vid, parts):
    slim = {"video_id": vid, "parts": [{"words": [{k: w[k] for k in ("text", "start", "type", "speaker_id") if w.get(k) is not None}
                                                  for w in p.get("words", [])]} for p in parts]}
    data = json.dumps(slim, ensure_ascii=False, separators=(",", ":")).encode()
    (OUT / f"{vid}.words.json.gz").write_bytes(gzip.compress(data, mtime=0))

def hms(s):
    s = int(s); return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"

def to_md(words, info):
    lines, cur, start = [], None, 0
    buf = []
    for w in words:
        if w.get("type") == "spacing":
            buf.append(w["text"]); continue
        spk = w.get("speaker_id") or "?"
        if spk != cur:
            if buf and cur is not None: lines.append(f"**[{hms(start)}] {cur}:** {''.join(buf).strip()}")
            cur, start, buf = spk, w.get("start", 0), []
        buf.append(w["text"])
    if buf: lines.append(f"**[{hms(start)}] {cur}:** {''.join(buf).strip()}")
    # Header lines stay in Spanish: tools/ingest.py parses them.
    head = (f"# {info.get('title', '')}\n\nFuente: {info.get('webpage_url', '')}\nCanal: {info.get('channel', '')}\n"
            f"Fecha de publicación: {info.get('upload_date', '')}\nDuración: {hms(info.get('duration') or 0)}\n"
            f"Transcripción automática: ElevenLabs Scribe v2 (diarización; los hablantes son speaker_N, sin identificar).\n")
    return head + "\n" + "\n\n".join(lines) + "\n"

if sys.argv[1:2] == ["--words"]:
    for f in sys.argv[2:]:
        write_words(Path(f).stem, json.loads(Path(f).read_text(encoding="utf-8"))["parts"])
    sys.exit()

os.makedirs(OUT, exist_ok=True)
for audio in sys.argv[1:]:
    vid = os.path.basename(audio).split(".")[0]
    if os.path.exists(f"{OUT}/{vid}.md") or os.path.exists(f"{OUT}/{vid}.fail"):
        print("SKIP", vid); continue
    info_path = os.path.splitext(audio)[0] + ".info.json"
    info = json.load(open(info_path)) if os.path.exists(info_path) else {}
    try:
        total = duration(audio)
        words, parts = [], []
        with tempfile.TemporaryDirectory() as tmp:
            offsets = list(range(0, int(total) + 1, CHUNK)) if total > CHUNK else [0]
            for off in offsets:
                src = audio
                if len(offsets) > 1:
                    src = f"{tmp}/{vid}_{off}.m4a"
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(off), "-t", str(CHUNK), "-i", audio, "-c", "copy", src], check=True)
                res = scribe(src)
                parts.append(res)
                for w in res.get("words", []):
                    for k in ("start", "end"):
                        if w.get(k) is not None: w[k] += off
                    if len(offsets) > 1 and w.get("speaker_id"):
                        # speaker ids restart in each chunk, so they are only comparable within one.
                        # The "tramoN-" prefix (Spanish for chunk) is kept so new and existing transcripts match.
                        w["speaker_id"] = f"tramo{off // CHUNK + 1}-{w['speaker_id']}"
                    words.append(w)
        json.dump({"video_id": vid, "parts": parts}, open(f"{OUT}/{vid}.json", "w"), ensure_ascii=False)
        write_words(vid, parts)
        open(f"{OUT}/{vid}.md", "w").write(to_md(words, info))
        print("OK", vid, hms(total), flush=True)
    except Exception as e:
        print("FAIL", vid, e, flush=True)
        open(f"{OUT}/{vid}.fail", "w").write(f"{e}\n")  # delete this file to retry
