#!/bin/bash
# usage: transcribe_queue.sh — transcribes finished downloads in sources/audiovisual/audio as they appear
# (3 at a time) until no yt-dlp is running and nothing is left.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; A=$ROOT/sources/audiovisual/audio; T=$ROOT/sources/audiovisual/transcripts
while true; do
  pend=$(for f in $A/*.m4a $A/*.webm $A/*.opus; do [ -f "$f" ] || continue; id=$(basename "${f%.*}"); [ -f "$T/$id.md" ] || [ -f "$T/$id.fail" ] || echo "$f"; done)
  if [ -z "$pend" ]; then pgrep -f "yt-dlp.*cookies-from-browser" >/dev/null || break; sleep 60; continue; fi
  echo "$pend" | head -6 | xargs -P 3 -n 1 python3 -I "$ROOT/scripts/acquisition/transcribe.py"
done
echo DONE
