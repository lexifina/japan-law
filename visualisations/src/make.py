"""Rebuild visualisations/20-no-gurafu-de-miru-nihon-no-horei.html from this repository.

    python visualisations/src/make.py [--repo PATH] [--ref REF] [--skip-extract]

Steps (all read-only on the repository; scratch output goes to visualisations/src/.build/):
  1. git log of REF, streamed: one line per commit with its author (the law that made the change), its subject, the
     trailers the charts use and the provisions its message lists as inserted, amended or removed  -> .build/log.tsv
  2. git log --name-status of REF for the Constitution and the six codes (old and new folder names) -> .build/codes-names.tsv
     and, for every commit, the number of files it wrote inside and outside suppl/                   -> .build/commit-files.tsv
  3. the tree of REF: every file of every law in force, with its blob id                           -> .build/tree.tsv
  4. the tables: laws.csv, corpus.json and data/laws.json, data/paths.json (whole), and from data/revisions.json the
     revision id of each row of laws.csv (the two list the same revisions in the same order)       -> .build/repo/, rev-ids.txt
  5. the blobs the charts read, listed from the tree of REF:
     - for every Act named by a file in suppl/ (the supplementary provisions an amending Act left in a law), the start
       of one such file: its heading gives the Act's date of promulgation, its first provision the day it took effect
                                                                                                      -> .build/suppl-heads.jsonl
     - every text file (main.md and the articles) of the laws numbered before 1947, and four of each law numbered from
       1947 to 1951 (main.md, the first, middle and last article), to tell the pre-war katakana style from hiragana
                                                                                                      -> .build/old-texts.jsonl
     - every article of the Constitution and of the six codes                                        -> .build/codes.jsonl
  6. prep.py turns those into .build/data.json; build.py fills page.tpl.html with it.
In a partial (blobless) clone the missing blobs are fetched in batches, some 20,000 small files in all; no other article
text is read. Nothing is held in memory at once that does not need to be: the history is streamed line by line.
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--repo', default=os.path.abspath(os.path.join(HERE, '..', '..')))
ap.add_argument('--ref', default=None, help='default: origin/main if present, else HEAD')
ap.add_argument('--out', default=os.path.join(HERE, '..', '20-no-gurafu-de-miru-nihon-no-horei.html'))
ap.add_argument('--skip-extract', action='store_true', help='reuse .build/ from a previous run (prep and build only)')
a = ap.parse_args()
B = os.path.join(HERE, '.build')
os.makedirs(B, exist_ok=True)
NOLAZY = dict(os.environ, GIT_NO_LAZY_FETCH='1')
GIT = ['git', '-C', a.repo, '-c', 'core.quotepath=off']


def git(*args, **kw):
    return subprocess.run([*GIT, *args], check=True, capture_output=True, env=NOLAZY, **kw).stdout


ref = a.ref
if not ref:
    ref = 'origin/main' if subprocess.run(['git', '-C', a.repo, 'rev-parse', '--verify', '-q', 'origin/main'], capture_output=True).returncode == 0 else 'HEAD'
sha = git('rev-parse', ref).decode().strip()
print('ref', ref, sha)


def fetch_missing(oids, batch=5000):
    """batched fetches for the blobs a partial clone does not have yet"""
    oids = sorted(set(oids))
    chk = subprocess.run([*GIT, 'cat-file', '--batch-check'], input=''.join(o + '\n' for o in oids).encode(),
                         capture_output=True, env=NOLAZY).stdout.decode().split('\n')
    missing = [l.split()[0] for l in chk if l.endswith(' missing')]
    for i in range(0, len(missing), batch):
        part = missing[i:i + batch]
        print('fetching', len(part), 'blobs', f'({i + len(part)} of {len(missing)})', flush=True)
        subprocess.run([*GIT, '-c', 'fetch.negotiationAlgorithm=noop', 'fetch', 'origin', '--no-tags', '--no-write-fetch-head',
                        '--recurse-submodules=no', '--filter=blob:none', '--stdin'], input=''.join(m + '\n' for m in part).encode(), check=False)


def read_blobs(items):
    """yield (path, bytes) for (oid, path) pairs, one blob at a time"""
    p = subprocess.Popen([*GIT, 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=NOLAZY)
    for oid, path in items:
        p.stdin.write((oid + '\n').encode()); p.stdin.flush()
        head = p.stdout.readline().split()
        if len(head) < 3:
            sys.exit('cannot read ' + path)
        data = p.stdout.read(int(head[2])); p.stdout.read(1)
        yield path, data
    p.stdin.close(); p.wait()


def jsonl(name, items, cut=None):
    with open(os.path.join(B, name), 'w', encoding='utf-8', newline='\n') as out:
        for path, data in read_blobs(items):
            t = data.decode('utf-8', 'replace')
            out.write(json.dumps({'p': path, 't': cut(t) if cut else t}, ensure_ascii=False) + '\n')


KINDS = ('constitution', 'act', 'cabinet-order', 'imperial-ordinance', 'dajokan-proclamation', 'dajokan-notice',
         'ministerial-ordinance', 'rule', 'regulation', 'pm-decision')


def split_law(path):
    """(law folder, the rest of the path) for a file of a law: <kind>/<year>/<number>/..., ministerial ordinances, rules
    and regulations under their issuer, joint ordinances under joint/<issuers>/"""
    p = path.split('/')
    if p[0] == 'constitution':
        d = 2
    elif p[0] in ('ministerial-ordinance', 'rule', 'regulation'):
        d = 5 if p[1] == 'joint' else 4
    else:
        d = 3
    return '/'.join(p[:d]), p[d:]


def art_key(name):
    """art-016-2.md (第十六条の二) -> (16, 2); a range of deleted articles, art-038-to-084.md, sorts by its first number"""
    m = re.match(r'^art-(\d+(?:-\d+)*)(?:-to-\d+(?:-\d+)*)?\.md$', name)
    return tuple(int(x) for x in m.group(1).split('-')) if m else None


CODES = ['constitution/1946', 'act/1896/089', 'act/1899/048', 'act/1907/045', 'act/1948/131', 'act/1996/109', 'act/2005/086']
OLD_CODES = ['kenpo', 'minpo', 'shoho', 'keiho', 'keiji-sosho', 'minji-sosho', 'kaisha']
TRAILERS = ['In-force', 'Promulgated', 'Stage', 'Kind', 'Label', 'Corrects', 'Revision', 'Act-path', 'Layout']

if not a.skip_extract:
    # 1. the history, streamed: one line per commit (a trailer that occurs more than once is joined with " ; ")
    fmt = '%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%s%x1f%(trailers:unfold,separator=%x1d)%x1f%b'
    lg = subprocess.Popen([*GIT, 'log', ref, '--format=' + fmt], stdout=subprocess.PIPE, env=NOLAZY)
    n, buf = 0, b''
    with open(os.path.join(B, 'log.tsv'), 'w', encoding='utf-8', newline='\n') as out:
        out.write('\t'.join(['i', 'sha', 'author', 'email', 'date', 'subject'] + TRAILERS + ['new', 'amended', 'removed']) + '\n')

        def emit(rec):
            global n
            rec = rec.decode('utf-8', 'replace').strip('\n')
            if not rec:
                return
            parts = rec.split('\x1f')
            tr = {}
            for t in (parts[5] if len(parts) > 5 else '').split('\x1d'):
                k, _, v = t.partition(': ')
                k = k.strip()
                if k and k != 'Files':
                    tr.setdefault(k, []).append(v.strip())
            ch = {'新設': '', '改正': '', '削除': ''}
            for line in (parts[6] if len(parts) > 6 else '').split('\n'):
                for k in ch:
                    if line.startswith(k + ' ('):
                        ch[k] = line.split('): ', 1)[1] if '): ' in line else ''
            row = [str(n)] + parts[:5] + [' ; '.join(tr.get(k, [])) for k in TRAILERS] + [ch['新設'], ch['改正'], ch['削除']]
            out.write('\t'.join(x.replace('\t', ' ').replace('\n', ' ') for x in row) + '\n')
            n += 1
        for chunk in iter(lambda: lg.stdout.read(1 << 16), b''):
            buf += chunk
            *recs, buf = buf.split(b'\x1e')
            for r in recs:
                emit(r)
        emit(buf)
    lg.wait()
    print('commits', n, flush=True)

    # 2. the files of each commit on the Constitution and the six codes (old and new folder names), streamed
    lg = subprocess.Popen([*GIT, 'log', ref, '--format=@@C %H', '--name-status', '--no-renames', '--', *CODES, *OLD_CODES], stdout=subprocess.PIPE, env=NOLAZY)
    nf, cur = 0, None
    with open(os.path.join(B, 'codes-names.tsv'), 'w', encoding='utf-8', newline='\n') as out:
        for raw in lg.stdout:
            l = raw.decode('utf-8', 'replace').rstrip('\n')
            if l.startswith('@@C '):
                cur = l[4:]
                continue
            if l and cur:
                st, _, f = l.partition('\t')
                out.write(f'{cur}\t{st[:1]}\t{f}\n')
                nf += 1
    lg.wait()
    print('code file changes', nf, flush=True)

    # 2b. for every commit, how many files it wrote in suppl/ (an amending law's supplementary provisions) and elsewhere
    lg = subprocess.Popen([*GIT, 'log', ref, '--format=@@C %H', '--name-only', '--no-renames'], stdout=subprocess.PIPE, env=NOLAZY)
    cur, ns, no = None, 0, 0
    with open(os.path.join(B, 'commit-files.tsv'), 'w', encoding='utf-8', newline='\n') as out:
        for raw in lg.stdout:
            l = raw.decode('utf-8', 'replace').rstrip('\n')
            if l.startswith('@@C '):
                if cur:
                    out.write(f'{cur}\t{ns}\t{no}\n')
                cur, ns, no = l[4:], 0, 0
            elif l:
                if '/suppl/' in l:
                    ns += 1
                else:
                    no += 1
        if cur:
            out.write(f'{cur}\t{ns}\t{no}\n')
    lg.wait()
    print('commit file counts written', flush=True)

    # 3. the tree on the last day of the record
    nt, laws = 0, {}
    tables = []
    with open(os.path.join(B, 'tree.tsv'), 'w', encoding='utf-8', newline='\n') as out:
        lt = subprocess.Popen([*GIT, 'ls-tree', '-r', '-z', ref], stdout=subprocess.PIPE, env=NOLAZY)
        buf = b''
        for chunk in iter(lambda: lt.stdout.read(1 << 16), b''):
            buf += chunk
            *ents, buf = buf.split(b'\0')
            for e in ents:
                meta, path = e.split(b'\t', 1)
                oid = meta.split()[2].decode()
                p = path.decode('utf-8')
                out.write(p + '\t' + oid + '\n')
                nt += 1
                if p in ('laws.csv', 'corpus.json', 'data/laws.json', 'data/paths.json', 'data/revisions.json'):
                    tables.append((oid, p))
        lt.wait()
    print('files in the tree', nt, 'tables', len(tables), flush=True)

    # 4. the tables (revisions.json is not kept: only the revision id of each of its revisions, in order)
    fetch_missing([o for o, _ in tables])
    R = os.path.join(B, 'repo')
    for path, data in read_blobs(tables):
        if path == 'data/revisions.json':
            ids = re.findall(rb'"law_revision_id":\s*"([^"]+)"', data)
            with open(os.path.join(B, 'rev-ids.txt'), 'w', encoding='utf-8', newline='\n') as out:
                out.write('\n'.join(i.decode() for i in ids) + '\n')
            print('revision ids', len(ids))
            del data, ids
            continue
        dst = os.path.join(R, *path.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as fh:
            fh.write(data)

    # 5. the blobs the charts read, chosen from the tree
    sup_first, old_files, code_files = {}, {}, []
    SUPAC = re.compile(r'^([mtshr])(\d+)-(\d+)\.md$')     # suppl/<era><year>-<number>.md: the provisions of an Act
    with open(os.path.join(B, 'tree.tsv'), encoding='utf-8') as fh:
        for line in fh:
            p, oid = line.rstrip('\n').split('\t')
            k0 = p.split('/', 1)[0]
            if k0 not in KINDS:
                continue
            fo, rest = split_law(p)
            if len(rest) == 2 and rest[0] == 'suppl':
                m = SUPAC.match(rest[1])
                if m:
                    key = f'{m.group(1)}{m.group(2)}-{m.group(3)}'
                    if key not in sup_first or p < sup_first[key][1]:
                        sup_first[key] = (oid, p)
            if fo in CODES and len(rest) == 1 and (art_key(rest[0]) or rest[0] == 'preamble.md'):
                code_files.append((oid, p))
            yr = fo.split('/')[-2] if k0 != 'constitution' else ''
            if yr[:4].isdigit() and int(yr[:4]) < 1952 and len(rest) == 1 and (art_key(rest[0]) or rest[0] == 'main.md'):
                old_files.setdefault(fo, []).append((oid, p))
    olds = []
    for fo, fs in old_files.items():
        mains = [f for f in fs if f[1].endswith('/main.md')]
        arts = sorted((f for f in fs if not f[1].endswith('/main.md')), key=lambda f: art_key(f[1].rsplit('/', 1)[1]))
        # every text file of a law numbered before 1947; four of those of 1947 to 1951, as a check
        pick = mains + arts if int(fo.split('/')[-2][:4]) < 1947 else mains + ([arts[0], arts[len(arts) // 2], arts[-1]] if arts else [])
        seen = set()
        for f in pick:
            if f[1] not in seen:
                seen.add(f[1]); olds.append(f)
    sups = sorted(sup_first.values(), key=lambda f: f[1])
    print('suppl heads', len(sups), 'old texts', len(olds), 'code articles', len(code_files), flush=True)
    fetch_missing([o for o, _ in sups + olds + code_files])

    def head(t, n=900):
        return t[:n]
    jsonl('suppl-heads.jsonl', sups, head)
    jsonl('old-texts.jsonl', olds)
    jsonl('codes.jsonl', code_files)

# 6. prep + build
env = dict(os.environ, HEAD_SHA=sha)
subprocess.run([sys.executable, '-X', 'utf8', os.path.join(HERE, 'prep.py'), B], check=True, env=env)
subprocess.run([sys.executable, '-X', 'utf8', os.path.join(HERE, 'build.py'), os.path.join(B, 'data.json'), os.path.abspath(a.out)], check=True)
