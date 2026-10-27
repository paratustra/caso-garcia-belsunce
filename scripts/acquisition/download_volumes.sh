#!/bin/bash
# usage: download_volumes.sh — for each sources/case-file/<volume>/ folder without its PDF: open its SlideShare page
# (url in source.json) in a Playwriter session, click "Download now", wait for the PDF in ~/Downloads, move it in.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; E=$ROOT/sources/case-file
newses() { SES=$(playwriter session new --tab-group corpus 2>&1 | grep -oE "Session [0-9]+" | grep -oE "[0-9]+"); echo $SES > "$ROOT/.session"; }
newses
cd "$ROOT"
for d in $E/*/; do
  n=$(basename "$d"); [ -f "$d/$n.pdf" ] && { echo "SKIP $n"; continue; }
  url=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1]))['url'])" "$d/source.json")
  loc=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1]))['loc'])" "$d/source.json")
  rm -f ~/Downloads/"$loc"*.pdf
  playwriter -s $SES --timeout 5000 -e "1" >/dev/null 2>&1 || newses
  playwriter -s $SES --timeout 90000 -e "
    if (!state.page || state.page.isClosed()) state.page = await context.newPage(); const p = state.page; await p.goto('$url', {waitUntil:'domcontentloaded', timeout:60000}); await p.waitForTimeout(3000);
    await p.getByRole('button', {name:/Download now/i}).or(p.getByRole('link', {name:/Download now/i})).first().click({timeout:20000});
    await p.waitForTimeout(2000);" 2>&1 | grep -iE "error" | head -2
  for i in $(seq 1 120); do
    f=$(ls ~/Downloads/"$loc"*.pdf 2>/dev/null | head -1)
    [ -n "$f" ] && [ ! -e "$f.crdownload" ] && sleep 2 && break; sleep 2
  done
  if [ -n "$f" ] && pdfinfo "$f" >/dev/null 2>&1; then
    mv "$f" "$d/$n.pdf"; rm -f ~/Downloads/"$loc"*.pdf
    echo "OK $n $(pdfinfo "$d/$n.pdf" | awk '/Pages/{print $2}') pages"
  else echo "FAIL $n"; fi
done
