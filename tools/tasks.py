"""Task queue. Definitions live in work/tasks.json (not edited while working);
state lives in work/claims/<id>/ (mkdir is atomic: two agents cannot claim the same task).

  python3 tools/tasks.py list [--family EXT]      # available tasks (dependencies done)
  python3 tools/tasks.py show EXT-exp-c01
  python3 tools/tasks.py claim EXT-exp-c01 --agent haiku-07
  python3 tools/tasks.py finish EXT-exp-c01 --agent haiku-07 --note "286 pages, 141 filings"
  python3 tools/tasks.py release EXT-exp-c01 --agent haiku-07 --note "reason"   # give back unfinished
  python3 tools/tasks.py reopen EXT-exp-c01 --agent auditor-2 --note "error rate 18 %"
Each action appends a line to work/log.md.
"""
import argparse
import json
import shutil
import sys
from datetime import datetime

from common import ROOT

WORK = ROOT / "work"
CLAIMS = WORK / "claims"


def state(tid):
    d = CLAIMS / tid
    if (d / "done").exists():
        return "done"
    return "claimed" if d.exists() else "pending"


def log(agent, tid, action, note):
    t = datetime.now().strftime("%Y-%m-%dT%H:%M")
    with open(WORK / "log.md", "a", encoding="utf-8") as fh:
        fh.write(f"{t} | {agent} | {tid} | {action} | {note or ''}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["list", "show", "claim", "finish", "release", "reopen"])
    ap.add_argument("id", nargs="?")
    ap.add_argument("--agent", default="unnamed")
    ap.add_argument("--note")
    ap.add_argument("--family")
    ap.add_argument("--all", action="store_true", help="also list claimed, done and blocked tasks")
    a = ap.parse_args()
    tasks = {t["id"]: t for t in json.loads((WORK / "tasks.json").read_text(encoding="utf-8"))["tasks"]}
    CLAIMS.mkdir(exist_ok=True)
    if a.action == "list":
        for t in tasks.values():
            if a.family and t["family"] != a.family:
                continue
            s = state(t["id"])
            ready = all(state(d) == "done" for d in t.get("depends_on", []))
            if a.all or (s == "pending" and ready):
                print(f"{t['id']:28} {s if ready else 'blocked':10} {t.get('model', ''):7} {t['title']}")
        return 0
    if a.id not in tasks:
        sys.exit(f"unknown task: {a.id}")
    d = CLAIMS / a.id
    if a.action == "show":
        print(json.dumps(tasks[a.id], ensure_ascii=False, indent=2), f"\nstate: {state(a.id)}")
        return 0
    if a.action == "claim":
        missing = [x for x in tasks[a.id].get("depends_on", []) if state(x) != "done"]
        if missing:
            sys.exit(f"blocked: waiting on {missing}")
        try:
            d.mkdir()
        except FileExistsError:
            sys.exit(f"{a.id} is already {state(a.id)} (agent: {(d / 'agent').read_text().strip() if (d / 'agent').exists() else '?'})")
        (d / "agent").write_text(a.agent + "\n")
    elif a.action == "finish":
        if not d.exists():
            sys.exit("claim it first")
        (d / "done").write_text((a.note or "") + "\n")
    elif a.action in ("release", "reopen"):
        shutil.rmtree(d, ignore_errors=True)
    log(a.agent, a.id, a.action, a.note)
    print(f"{a.id}: {state(a.id)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
