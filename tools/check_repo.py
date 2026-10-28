"""Checks the git repository against the official text: every revision of every act in e-Gov, read back from git with
tools/jiten.py on the day it took effect, must equal that revision's full text.

    python -X utf8 scripts/japan-law/check_repo.py [--repo ../japan-law] [--no-record]

Two checks per revision, from the cached e-Gov law XML (no network):
1. File by file: the act's files in git on that day are exactly the files the build's parser makes from that
   revision's XML (same set of files, same bytes).
2. Word for word: the whole act printed by jiten.py, with its markdown marks removed, has the same words in the same
   order as the whole official text, read independently of the parser: every text node of <Law> in document order
   (ruby readings, <Rt>, left out, as the build leaves them out), with the amending law's number of each supplementary
   provision (its AmendLawNum attribute, in brackets as the build prints it) after its label, joined with a space only at the boundary of a block element.
   Japanese has no spaces between words, so a word here is a run of letters between punctuation or block boundaries.
Revisions not yet in force are read from the branch "mishiko". The result is written to verification.json next to
this script (unless --no-record), for REPRODUCE.md.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from lxml import etree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

TOKEN = re.compile(r'\w+|[^\w\s]')
INLINE = {'Ruby', 'Sup', 'Sub', 'Line', 'Sentence'}


def official_words(raw: bytes) -> list[str]:
    law = etree.fromstring(raw).find('law_full_text/Law')
    parts: list[str] = []

    def walk(e):
        if e.tag == 'Rt':
            parts.append(e.tail or '')
            return
        gap = '' if e.tag in INLINE else ' '
        parts.append(gap + (e.text or ''))
        if e.tag == 'SupplProvisionLabel' and e.getparent().get('AmendLawNum'):
            parts.append(' （' + e.getparent().get('AmendLawNum') + '） ')
        for c in e:
            if isinstance(c.tag, str):
                walk(c)
            else:
                parts.append(c.tail or '')
        parts.append(gap + (e.tail or ''))
    walk(law)
    return TOKEN.findall(''.join(parts))


def repo_words(text: str) -> list[str]:
    lines = []
    for l in text.split('\n'):
        l = re.sub(r'^\s*(#+ |- )', '', l)
        if l.startswith('| ') and l.endswith(' |'):
            l = l[2:-2].replace(' | ', ' ')   # the cell separators of a table row
        lines.append(l)
    return TOKEN.findall(' '.join(lines))


def tool(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, 'tools/jiten.py', *args], cwd=repo, capture_output=True, text=True,
                          encoding='utf-8')


def files_at(repo: str, commit: str, slug: str) -> dict[str, str]:
    """The act's files at a commit, read with one ls-tree and one cat-file --batch (not one git show per file)."""
    out = subprocess.run(['git', 'ls-tree', '-r', commit, f'{slug}/'], cwd=repo, capture_output=True,
                         text=True, encoding='utf-8').stdout.split('\n')
    blobs = []
    for line in out:
        if not line:
            continue
        info, f = line.split('\t', 1)
        if f.endswith('.md') and not f.endswith('/README.md'):
            blobs.append((f[len(slug) + 1:], info.split()[2]))
    if not blobs:
        return {}
    data = subprocess.run(['git', 'cat-file', '--batch'], cwd=repo, input=''.join(f'{sha}\n' for _, sha in blobs).encode(),
                          capture_output=True).stdout
    res, pos = {}, 0
    for name, _ in blobs:
        nl = data.index(b'\n', pos)
        size = int(data[pos:nl].split()[2])
        res[name] = data[nl + 1:nl + 1 + size].decode('utf-8')
        pos = nl + 1 + size + 1
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(build.ROOT.parent / 'japan-law'))
    ap.add_argument('--no-record', action='store_true')
    args = ap.parse_args()
    versions = files = bad = words = wbad = 0
    nwords = 0
    per_act = {}
    for act in build.ACTS:
        _, revs = build.revisions(act, offline=True)
        for v in revs:
            raw = build.fetch(v['url'], offline=True)
            parsed = build.read_version(raw)
            expected = {build.file_name(k): u['text'] for k, u in parsed['units'].items()}
            commit = subprocess.run([sys.executable, '-B', '-c', 'import sys; sys.path.insert(0, "tools"); import jiten; '
                                     f'print(jiten.commit_on("{v["from"]}", "{act["slug"]}"))'],
                                    cwd=args.repo, capture_output=True, text=True).stdout.strip()
            got = files_at(args.repo, commit, act['slug']) if commit else {}
            # Two revisions on one day: git holds the last one on that day; check the earlier one at its own commit.
            same_day = [w for w in revs if w['from'] == v['from']]
            if len(same_day) > 1 and same_day[-1] is not v:
                commit = subprocess.run(['git', 'log', '--all', '--format=%H', f'--grep=^Revision: {v["id"]}'],
                                        cwd=args.repo, capture_output=True, text=True).stdout.split()[0]
                got = files_at(args.repo, commit, act['slug'])
            versions += 1
            per_act[act['slug']] = per_act.get(act['slug'], 0) + 1
            files += len(expected)
            if got != expected:
                bad += 1
                diff = sorted(set(got) ^ set(expected)) or [k for k in expected if got.get(k) != expected[k]]
                print(f'MISMATCH {act["slug"]} {v["id"]}: {diff[:5]}')
            if len(same_day) > 1 and same_day[-1] is not v:
                text = ''.join(got[f] + '\n' for f in sorted(got, key=lambda f: build.unit_order(f[:-3])))
                rc = 0
            else:
                whole = tool(args.repo, v['from'], act['slug'])
                text, rc = whole.stdout, whole.returncode
            words += 1
            ow, rw = official_words(raw), repo_words(text)
            nwords += len(ow)
            if rc or ow != rw:
                wbad += 1
                i = next((i for i, (a, b) in enumerate(zip(ow, rw)) if a != b), min(len(ow), len(rw)))
                print(f'WORDS {act["slug"]} {v["id"]}: official {len(ow)} vs repo {len(rw)} words; first difference at '
                      f'{i}: {" ".join(ow[max(0, i - 5):i + 5])!r} / {" ".join(rw[max(0, i - 5):i + 5])!r}')
    print(f'{versions} revisions checked ({files} files), {bad} mismatches; {words} revisions word for word '
          f'({nwords} words), {wbad} mismatches')
    print('per act:', per_act)
    if not args.no_record:
        p = HERE / 'verification.json'
        rec = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        rec['check'] = {'versions': versions, 'files': files, 'mismatches': bad, 'wordcheck': words,
                        'words': nwords, 'word_mismatches': wbad, 'per_act': per_act}
        p.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    raise SystemExit(1 if bad or wbad else 0)


if __name__ == '__main__':
    main()
