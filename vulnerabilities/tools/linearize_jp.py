"""japan-law keeps its history out of date order: each act was first published as its current text (Kind: baseline),
then its earlier versions were appended oldest first as correction commits (Kind: correction, Reason: earlier version
back-filled ...), each holding the act's whole tree as it stood from its In-force day, and a last correction set the
current text back at the tip (Reason: the text in force now, restored ...), credited to e-Gov. A plain `git log --raw`
therefore diffs the oldest version against today's text, and every version sits under the act's folder name before the
layout move of 2026-11-10 (data/paths.json).

This rebuilds index/changes/japan-law.parquet and the corpus's rows in index/root.parquet in date order (run after
add_root.py):
  - each act's versions are its correction commits sorted by In-force (its baseline commit is the same text as the
    restore commit and is set aside as kind 'superseded'); an act with no history has its baseline only;
  - each version is diffed against the act as it stood in the version before it (the first against nothing, kind
    'baseline'), and every path is given under the act's current folder;
  - every later version is kind 'law', credited to the amending law named in its author; the restore commit, which the
    repository credits to e-Gov, is credited to the law in its Revision: trailer (the same name the back-filled
    versions use for that law; for an Act or Cabinet Order none of them names, a name in the same form built from the
    id; otherwise 'e-Gov law ID <id>').
Commits that are not act versions (documentation, the layout move) keep their rows as they were; the eight acts kept
under a short name (minpo/, kaisha/ ...) have ordinary dated law commits (no Kind:), whose rows are only moved to the
acts' current folders."""
import json, os, re, subprocess, sys
from collections import defaultdict
import duckdb, pyarrow as pa, pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
pin = json.load(open(os.path.join(HERE, "pins.json"), encoding="utf-8"))["corpora"][0]
REPO = os.path.join(HERE, "sources", "corpus", pin["repo"] + ".git")
IDX = os.path.join(HERE, "index")
CH = os.path.join(IDX, "changes", pin["repo"] + ".parquet")
EMPTY = "4b825dc642cb6eb9a060e54bf8d69288fbe4904"
FLAGS = 0x08000000 if sys.platform == "win32" else 0


def git(*a, inp=None):
    return subprocess.run(["git", "-c", "core.quotepath=off", *a], cwd=REPO, input=inp, capture_output=True, check=True,
                          creationflags=FLAGS).stdout.decode("utf-8")


paths = json.loads(git("show", f"{pin['sha']}:data/paths.json"))["paths"]
con = duckdb.connect()
cm = con.sql(f"""select commit, author_date, json_extract_string(trailers,'$.Kind[0]') kind,
    json_extract_string(trailers,'$."Act-path"[0]') ap, json_extract_string(trailers,'$."In-force"[0]') inf,
    coalesce(json_extract_string(trailers,'$.Reason[0]'), '') reason, json_extract_string(trailers,'$.Revision[0]') rev
    from '{IDX}/commits/{pin['repo']}.parquet'""").fetchall()
info = {r[0]: r for r in cm}
# a baseline commit has no Act-path: its act is the one folder its files are in
base_folder = dict(con.sql(f"""select commit, any_value(split_part(path, '/', 1)) from '{CH}'
    where commit in (select commit from '{IDX}/commits/{pin['repo']}.parquet' where json_extract_string(trailers,'$.Kind[0]') = 'baseline')
      and path like '%/%' group by commit having count(distinct split_part(path, '/', 1)) = 1""").fetchall())
authors = dict(l.split("\x1f", 1) for l in git("log", "--format=%H\x1f%an", pin["sha"]).splitlines())

acts = defaultdict(lambda: {"base": [], "ver": []})
for sha, ad, kind, ap, inf, reason, rev in cm:
    if kind == "baseline" and sha in base_folder:
        acts[base_folder[sha]]["base"].append(sha)
    elif kind == "correction" and ap:
        acts[ap]["ver"].append(sha)
missing = [a for a in acts if a not in paths]
print(f"acts {len(acts):,}; with history {sum(1 for a in acts.values() if a['ver']):,}; not in data/paths.json {len(missing)}", flush=True)

# the amending law of each revision id, as the back-filled versions name it
law_of = {}
for sha, ad, kind, ap, inf, reason, rev in cm:
    if kind == "correction" and reason.startswith("earlier version") and rev and rev.count("_") == 2:
        a = authors[sha]
        if not a.startswith("e-Gov"):
            law_of.setdefault(rev.split("_")[2], a)

ERAS = {"1": ("明治", 1867), "2": ("大正", 1911), "3": ("昭和", 1925), "4": ("平成", 1988), "5": ("令和", 2018)}


def kanji(n):
    d = "〇一二三四五六七八九"
    s = ""
    for v, u in ((1000, "千"), (100, "百"), (10, "十")):
        q, n = divmod(n, v)
        if q:
            s += ("" if q == 1 else d[q]) + u
    return s + (d[n] if n else "")


def name_of(i):
    """an Act or Cabinet Order named the way the back-filled versions name it: 令和三年政令第二百三十一号 (Cabinet Order No. 231 of 2021)"""
    m = re.fullmatch(r"([1-5])(\d\d)(AC|CO)(\d{10})", i)
    if not m:
        return None
    era, base = ERAS[m.group(1)]
    y, n = int(m.group(2)), int(m.group(4))
    if not 0 < n < 10000:
        return None
    jp, en = ("法律", "Act") if m.group(3) == "AC" else ("政令", "Cabinet Order")
    return f"{era}{'元' if y == 1 else kanji(y)}年{jp}第{kanji(n)}号 ({en} No. {n} of {base + y})"


order, kind_of, law_new = [], {}, {}
for act, a in acts.items():
    if a["ver"]:
        vs = sorted(a["ver"], key=lambda s: (info[s][4] or "", 1 if info[s][5].startswith("the text in force now") else 0))
        for s in a["base"]:
            kind_of[s] = "superseded"
    else:
        vs = sorted(a["base"], key=lambda s: info[s][4] or "")
    prev = None
    for i, s in enumerate(vs):
        kind_of[s] = "baseline" if i == 0 else "law"
        if info[s][5].startswith("the text in force now"):
            amend = (info[s][6] or "__").split("_")[2] if (info[s][6] or "").count("_") == 2 else ""
            law_new[s] = law_of.get(amend) or name_of(amend) or (f"e-Gov law ID {amend}" if amend and set(amend) != {"0"} else authors[s])
        order.append((act, prev, s))
        prev = s

# tree of each act folder in each version
need = sorted({(s, act) for act, p, s in order} | {(p, act) for act, p, s in order if p})
out = git("cat-file", "--batch-check", inp=("".join(f"{s}:{a}\n" for s, a in need)).encode())
tree = {}
for (s, a), line in zip(need, out.splitlines()):
    f = line.split()
    tree[(s, a)] = f[0] if len(f) >= 2 and f[1] == "tree" else None
pairs = []
for act, p, s in order:
    t1 = tree.get((p, act)) if p else EMPTY
    t2 = tree.get((s, act))
    if t1 and t2:
        pairs.append((act, s, t1, t2))
print(f"versions {len(order):,}; diffs {len(pairs):,}", flush=True)
uniq = sorted({(t1, t2) for _, _, t1, t2 in pairs if t1 != EMPTY})
diff = defaultdict(list)
from concurrent.futures import ThreadPoolExecutor   # a first version: every file added (the mirror has no empty tree object)


def added(t2):
    rows = []
    for line in git("ls-tree", "-r", t2).splitlines():
        meta, _, p = line.partition("\t")
        f = meta.split()
        if f[1] == "blob":
            rows.append(("A", "0" * 40, f[2], p, p))
    return t2, rows


with ThreadPoolExecutor(6) as ex:
    for t2, rows in ex.map(added, sorted({t2 for _, _, t1, t2 in pairs if t1 == EMPTY})):
        diff[(EMPTY, t2)] = rows
raw = git("diff-tree", "--stdin", "-r", "-M", "--raw", "--no-abbrev", inp=("".join(f"{a} {b}\n" for a, b in uniq)).encode())
cur = None
for line in raw.splitlines():
    if line.startswith(":"):
        meta, _, rest = line.partition("\t")
        f = meta[1:].split()
        ps = rest.split("\t")
        diff[cur].append((f[4], f[2], f[3], ps[0], ps[-1]))
    elif re.fullmatch(r"[0-9a-f]{40} [0-9a-f]{40}", line.strip()):
        cur = tuple(line.split())

C = {k: [] for k in ("commit", "author_date", "status", "old_blob", "new_blob", "old_path", "path")}
version_commits = set(kind_of)
old = pq.read_table(CH).to_pylist()
def moved(p):  # the eight acts kept by short name (minpo/, kaisha/ ...) have ordinary law commits: current folder
    a, _, rest = p.partition("/")
    return f"{paths[a]}/{rest}" if rest and a in paths else p


for r in old:  # rows of commits that are not act versions stay as they were, under the acts' current folders
    if r["commit"] not in version_commits:
        if info.get(r["commit"], (None,) * 3)[2] is None:   # no Kind: an ordinary law commit
            r["path"], r["old_path"] = moved(r["path"]), moved(r["old_path"])
        for k in C:
            C[k].append(r[k])
kept = len(C["commit"])
for act, s, t1, t2 in pairs:
    new = paths.get(act, act)
    for st, ob, nb, op, np_ in diff.get((t1, t2), []):
        C["commit"].append(s); C["author_date"].append(info[s][1]); C["status"].append(st)
        C["old_blob"].append(ob); C["new_blob"].append(nb)
        C["old_path"].append(f"{new}/{op}"); C["path"].append(f"{new}/{np_}")
t = pa.table(C).append_column("corpus", pa.array([pin["path"]] * len(C["commit"]), pa.string()))
pq.write_table(t, CH + ".new", compression="zstd")
os.replace(CH + ".new", CH)
print(f"changes: {len(old):,} rows before, {t.num_rows:,} after ({kept:,} kept from commits that are not act versions)", flush=True)

con.register("k", pa.table({"c": list(kind_of), "k": [kind_of[c] for c in kind_of],
                            "l": [law_new.get(c) for c in kind_of]}))
R = os.path.join(IDX, "root.parquet").replace("\\", "/")
con.sql(f"""copy (select r.root, r.corpus, r.corpus_commit, coalesce(k.l, r.law) law, r.in_force,
                         coalesce(k.k, r.kind) kind, r.subject
                  from '{R}' r left join k on k.c = r.corpus_commit and r.corpus = '{pin['path']}')
           to '{R}.new' (format parquet, compression zstd)""")
os.replace(R + ".new", R)
print(con.sql(f"select kind, count(*) from '{R}' where corpus = '{pin['path']}' group by 1 order by 2 desc").fetchall())
print("restore commits credited:", sum(1 for v in law_new.values() if not v.startswith(("e-Gov law ID", "e-Gov 法令検索"))), "by name,",
      sum(1 for v in law_new.values() if v.startswith("e-Gov law ID")), "by id,", sum(1 for v in law_new.values() if v.startswith("e-Gov 法令検索")), "left to e-Gov")
