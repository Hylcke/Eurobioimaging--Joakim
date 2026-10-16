"""Check that every link the Node pages would show actually opens.

Usage (on a computer with normal internet access):
    python check_links.py            # check every link, about 5-10 minutes
    python check_links.py --recheck  # only links that failed last time

Links checked: Node websites (August master), Access Portal pages, and every
facility website in the Knowledge Base Master.

Writes link_status.json: {url: {"ok": bool, "status": code or error, "final_url", "checked_at"}}.
A link counts as working when it answers with a 2xx page after redirects.
Sites that block automated checks (401, 403, 429) are marked BOT_BLOCKED and
left off the pages. Open those by hand; if one works, add a line to
link_overrides.csv:  url,ok,checked_by,date
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
from datetime import datetime, timezone

import requests

from kbdata import LINK_STATUS, august_node_map, load_august, load_kb, s, urls_in

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36 Euro-BioImaging link check")


def check(url: str) -> dict:
    out = {"checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"}, timeout=25,
                         allow_redirects=True, stream=True)
        r.close()
        out.update(status=r.status_code, final_url=r.url, ok=200 <= r.status_code < 300)
        if r.status_code in (401, 403, 429):
            out["note"] = "BOT_BLOCKED: open by hand"
    except requests.RequestException as exc:
        out.update(status=type(exc).__name__, final_url=None, ok=False)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recheck", action="store_true")
    args = ap.parse_args()

    kb, aug = load_kb(), load_august()
    links = set()
    for n in kb["Nodes"]:
        links.update(urls_in(n.get("access_portal_url")))
    for row in august_node_map(kb, aug).values():
        links.update(urls_in(row.get("Node website")))
        links.update(urls_in(row.get("Access Portal URL")))
    for f in kb["Facilities"]:
        links.update(urls_in(f.get("website"))[:1])
    old = json.loads(LINK_STATUS.read_text(encoding="utf-8")) if LINK_STATUS.exists() else {}
    todo = sorted(u for u in links if not (args.recheck and old.get(u, {}).get("ok")))
    print(f"Checking {len(todo)} links ...", flush=True)
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for url, res in zip(todo, ex.map(check, todo)):
            old[url] = res
    LINK_STATUS.write_text(json.dumps(dict(sorted(old.items())), ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for u in links if old.get(u, {}).get("ok"))
    blocked = [u for u in links if "BOT_BLOCKED" in s(old.get(u, {}).get("note"))]
    print(f"{ok} of {len(links)} links work. {len(blocked)} block automated checks (open by hand). "
          f"{len(links) - ok - len(blocked)} fail.")
    for u in sorted(links):
        r = old.get(u, {})
        if not r.get("ok"):
            print(f"  {r.get('status')}  {u}")
    print(f"Saved {LINK_STATUS}")


if __name__ == "__main__":
    main()
