"""Hand-check helper for empty periods that survived the review: in the extending version's diff, the removed lines that
hold the old date and the added lines that hold the new one (dates read as the time-limit search reads them), the
version before (with its law and day), and the extending law's supplementary provisions in the act, if the record holds them.

    python -X utf8 late_ext_check.py [path-substring]"""
import difflib, json, os, subprocess, sys
import duckdb
D = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(D, "gl", "vulnerabilities", "scripts")
sys.path.insert(0, os.path.join(S, "ingest"))
from textscan import limits  # noqa: E402
G = os.path.join(S, "sources", "corpus", "japan-law.git")
recs = [json.loads(l) for l in open(os.path.join(S, "findings", "run", "late_extension_triage.jsonl"), encoding="utf-8")]
surv = [r["row"] for r in recs if r["j"]["verdict"] == "candidate_gap" and (r.get("rebut") or {}).get("survives")]
sel = sys.argv[1] if len(sys.argv) > 1 else ""


def blob(b):
    return "" if not b or set(b) == {"0"} else subprocess.run(["git", "cat-file", "blob", b], cwd=G, capture_output=True).stdout.decode("utf-8")


con = duckdb.connect()
for x in surv:
    if sel not in x["path"]:
        continue
    rows = con.execute(f"""select r.in_force, r.law, ch.old_blob, ch.new_blob, ch.commit from '{S}/index/changes/japan-law.parquet' ch
        join '{S}/index/root.parquet' r on r.corpus_commit = ch.commit where ch.path = ? and r.kind in ('law','baseline') order by r.in_force""",
                       [x["path"]]).fetchall()
    print(f"\n######## {x['path']}  {x['old_until']} -> {x['new_until']}  by {x['law']} in force {x['extended_in_force']} (gap {x['gap_days']})")
    print("   versions:", ", ".join(f"{r[0]}" for r in rows))
    for i, (inf, law, ob, nb, c) in enumerate(rows):
        if inf[:10] != x["extended_in_force"]:
            continue
        a, b = blob(ob).splitlines(), blob(nb).splitlines()
        rem = [l for l in a if l not in set(b) and any(d == x["old_until"] for d, _ in limits(l))]
        add = [l for l in b if l not in set(a) and any(d == x["new_until"] for d, _ in limits(l))]
        print("   previous version:", rows[i - 1][0] if i else "-", "| commit", c[:10])
        for l in rem[:3]:
            print("   - ", l[:400])
        for l in add[:3]:
            print("   + ", l[:400])
        if not rem:
            print("   (no removed line holds the old date)")
