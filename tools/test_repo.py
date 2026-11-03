"""Functional smoke test of the built Japanese law repository: the things a reader does with it work. Standard library
only.

    python -X utf8 scripts/japan-law/test_repo.py [--repo ../japan-law] [--record]
    python -X utf8 tools/test_repo.py                   # from inside the repository

It asserts that:
1. `git blame` on a changed provision names amending laws as authors of its lines;
2. tools/jiten.py gives the text before and after a known amendment, and each equals the file at that day's tag;
3. `git log --follow` on a file lists its amending laws in the order they took effect;
4. every tag resolves to a commit, and every commit has an `In-force:` trailer, and every trailer block parses;
5. every commit authored by Lexifina is a documentation commit (the last one is one), and every commit by the
   publisher is a labelled baseline or a labelled correction (Kind: correction);
6. every git or tool command in the README's table runs and prints something;
7. the branch mishiko contains main and holds only changes not yet in force, or changes that have since come into
   force and are on main too (same e-Gov revision).
With --record the result is written to verification.json next to this script (for REPRODUCE.md).
"""
import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAW = re.compile(r'^(明治|大正|昭和|平成|令和)\S+年\S*第\S+号 \([A-Za-z ]+ No\. \d+ of \d{4}\)$|^日本国憲法 \(The Constitution of Japan\)$')
PUBLISHER = 'e-Gov 法令検索 (デジタル庁)'


def default_repo() -> Path:
    if (HERE.parent / '.git').exists():
        return HERE.parent
    return HERE.parents[2] / 'japan-law'


class Smoke:
    def __init__(self, repo: Path, since: str = ''):
        self.repo = repo
        self.since = since
        self.results: list[tuple[str, bool, str]] = []

    def git(self, *args: str) -> str:
        out = subprocess.run(['git', *args], cwd=self.repo, capture_output=True, text=True, encoding='utf-8')
        if out.returncode:
            raise AssertionError(f'git {" ".join(args)}: {out.stderr.strip()}')
        return out.stdout

    def tool(self, *args: str) -> str:
        out = subprocess.run([sys.executable, 'tools/jiten.py', *args], cwd=self.repo, capture_output=True, text=True,
                             encoding='utf-8')
        if out.returncode:
            raise AssertionError(f'jiten {" ".join(args)}: {out.stderr.strip()}')
        return out.stdout

    def check(self, name: str, fn):
        try:
            detail = fn() or ''
            self.results.append((name, True, detail))
            print(f'PASS {name}: {detail}')
        except AssertionError as exc:
            self.results.append((name, False, str(exc)))
            print(f'FAIL {name}: {exc}')

    # 1
    def blame(self):
        out = self.git('blame', '--line-porcelain', 'main', '--', 'kojin-joho/art-002.md')
        authors = {l[7:] for l in out.splitlines() if l.startswith('author ')}
        assert authors, 'no blame output'
        assert all(LAW.match(a) or a == PUBLISHER for a in authors), f'unexpected authors {authors}'
        laws = {a for a in authors if LAW.match(a)}
        assert '令和三年法律第三十七号 (Act No. 37 of 2021)' in laws, f'令和三年法律第三十七号 not among {authors}'
        assert len(laws) >= 2, f'only {laws}'
        return f'kojin-joho/art-002.md lines by {", ".join(sorted(authors))}'

    # 2
    def on_date(self):
        done = []
        for act, prov, path, tag, before, after in [
                ('kojin-joho', '1', 'kojin-joho/art-001.md', 'ac/2021-37/2022-04-01', '2022-03-31', '2022-04-01'),
                ('kojin-joho', '132', 'kojin-joho/art-132.md', 'ac/2024-46', '2025-03-31', '2025-04-01')]:
            a, b = self.tool(before, act, prov), self.tool(after, act, prov)
            assert a and b and a != b, f'{path}: no change between {before} and {after}'
            assert b == self.git('show', f'{tag}:{path}'), f'{path} on {after} is not the file at {tag}'
            assert a == self.git('show', f'{tag}~1:{path}'), f'{path} on {before} is not the file before {tag}'
            done.append(f'{path} {before} != {after}')
        whole = self.tool('2000-01-01', 'kenpo')
        assert '第九条　日本国民は' in whole, 'whole Constitution on 2000-01-01 lacks 第九条'
        early = subprocess.run([sys.executable, 'tools/jiten.py', '2016-12-31', 'kojin-joho'], cwd=self.repo,
                               capture_output=True, text=True, encoding='utf-8')
        assert early.returncode != 0, 'jiten printed the APPI before its record begins'
        return '; '.join(done) + '; kenpo 第九条 on 2000-01-01; APPI before 2017-03-01 refused'

    # 3
    def follow(self):
        checked = []
        for path in ('kojin-joho/art-002.md', 'kojin-joho/art-027.md', 'kojin-joho/appdx/table-1.md'):
            out = self.git('log', '--follow', '--format=%an%x09%(trailers:key=In-force,valueonly,separator=)', 'main', '--', path)
            rows = [l.split('\t') for l in out.splitlines() if l]
            assert len(rows) >= 2, f'{path}: {len(rows)} commits'
            days = [d.strip() for _, d in rows]
            assert days == sorted(days, reverse=True), f'{path}: not in date order {days}'
            assert all(LAW.match(a) or a in (PUBLISHER, 'Lexifina') for a, _ in rows), f'{path}: authors {[a for a, _ in rows]}'
            assert sum(1 for a, _ in rows if LAW.match(a)) >= 2, f'{path}: fewer than two laws'
            checked.append(f'{path} {len(rows)} commits')
        return '; '.join(checked)

    # 4
    def tags_and_trailers(self):
        tags = self.git('tag').split()
        assert tags, 'no tags'
        for t in tags:
            self.git('rev-parse', '--verify', '-q', f'{t}^{{commit}}')
        rows = self.git('log', '--format=%H%x09%an%x09%(trailers:key=In-force,valueonly,separator=)', 'main', 'mishiko',
                        '--no-merges').splitlines()
        # Trailer blocks are parsed one commit at a time; with --since, only the commits added after that one.
        recent = set(self.git('rev-list', '--no-merges', 'main', 'mishiko', f'^{self.since}').split()) if self.since else None
        bad = [r for r in rows if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', r.split('\t')[2].strip())]
        assert not bad, f'{len(bad)} commits without a well-formed In-force, e.g. {bad[:2]}'
        # git's own trailer parser (%(trailers:only)) must give back the whole last paragraph of each message: one
        # `git log` for all of them, rather than one `git interpret-trailers` per commit.
        unparsed = []
        out = self.git('log', '--no-merges', '--format=%H%x00%(trailers:only,unfold)%x00%B%x01', 'main', 'mishiko')
        for rec in out.split('\x01'):
            if '\x00' not in rec:
                continue
            h, parsed, body = rec.lstrip('\n').split('\x00', 2)
            if recent is not None and h not in recent:
                continue
            last = body.rstrip('\n').split('\n\n')[-1]
            if parsed.strip() != last.strip():
                unparsed.append(h[:10])
        assert not unparsed, f'trailer blocks git does not parse: {unparsed[:3]}'
        objs = subprocess.run(['git', 'cat-file', '--batch'], cwd=self.repo, capture_output=True,
                              input=''.join(r.split('\t')[0] + '\n' for r in rows).encode()).stdout
        assert b'\r' not in objs, 'a commit object holds a carriage return (CRLF message)'
        parsed_n = len(rows) if recent is None else len(recent)
        return (f'{len(tags)} tags resolve; {len(rows)} commits carry In-force; the trailer blocks of {parsed_n} commits '
                'parse; no CR in any commit object')

    # 5
    def lexifina(self):
        rows = self.git('log', '--format=%H%x09%an%x09%ae%x09%cn%x09%B%x1e', 'main').split('\x1e')
        rows = [r.strip('\n').split('\t', 4) for r in rows if r.strip()]
        by_lex = [r for r in rows if r[1] == 'Lexifina']
        assert by_lex and by_lex[0] == rows[0], 'the last commit is not the documentation commit'
        assert all('Kind: documentation' in r[4] for r in by_lex), 'a commit by Lexifina that is not documentation'
        assert all(r[3] == 'Lexifina' for r in rows), 'a committer other than Lexifina'
        pub = [r for r in rows if r[1] == PUBLISHER]
        # The publisher's commits are labelled: a baseline (a consolidated first text), or a correction of the history
        # pass (an earlier version found in e-Gov's record before any law's, or the text in force now set back).
        assert pub and all('Kind: baseline' in r[4] or 'Kind: correction' in r[4] for r in pub), \
            f'{len(pub)} publisher commits, or one not labelled'
        laws = [r for r in rows if r[1] != 'Lexifina']
        authors = {r[1] for r in laws}
        assert all(LAW.match(a) or a == PUBLISHER for a in authors), f'unexpected authors {sorted(authors - {PUBLISHER})[:5]}'
        assert all(r[2].endswith('.invalid') for r in laws), 'an author address that is not .invalid'
        return (f'{len(by_lex)} documentation commits by Lexifina, the last one on top; {len(pub)} labelled baselines; '
                f'{len(authors)} authors')

    # 6
    def readme(self):
        text = (self.repo / 'README.md').read_text(encoding='utf-8')
        table = text[text.index('## The questions'):text.index('## The dates')]
        cmds = [c for c in re.findall(r'`([^`]+)`', table) if c.startswith(('git ', 'python '))]
        assert len(cmds) >= 10, f'only {len(cmds)} commands found'
        for c in cmds:
            args = shlex.split(c)
            if args[0] == 'python':
                args[0] = sys.executable
            out = subprocess.run(args, cwd=self.repo, capture_output=True, text=True, encoding='utf-8')
            assert out.returncode == 0, f'{c}: exit {out.returncode} {out.stderr.strip()[:200]}'
            assert out.stdout.strip(), f'{c}: printed nothing'
        return f'{len(cmds)} README commands ran and printed output'

    # 7
    def future(self):
        base = self.git('merge-base', 'main', 'mishiko').strip()
        main = self.git('rev-parse', 'main').strip()
        assert base == main, 'mishiko does not contain main'
        built = json.loads((self.repo / 'corpus.json').read_text(encoding='utf-8'))['built']
        fmt = '--format=%(trailers:key=In-force,valueonly,separator=)%x09%(trailers:key=Revision,valueonly,separator=)'
        rows = [l.split('\t') for l in self.git('log', '--no-merges', fmt, 'main..mishiko').splitlines() if l]
        on_main = {l.split('\t')[1] for l in self.git('log', fmt, 'main').splitlines() if '\t' in l}
        matured = [r for r in rows if r[0] <= built]
        assert rows and all(r[1] in on_main for r in matured), \
            f'mishiko holds changes in force by {built} that main lacks: {[r for r in matured if r[1] not in on_main]}'
        main_days = self.git('log', '--format=%(trailers:key=In-force,valueonly,separator=)', 'main').split()
        assert all(d <= built for d in main_days), 'main holds a change not yet in force'
        return (f'{len(rows) - len(matured)} commits not yet in force, all after {built}; {len(matured)} since in force, '
                'and on main too; main has none after that day')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=None)
    ap.add_argument('--record', action='store_true')
    ap.add_argument('--since', default='', help='parse the trailer blocks only of commits after this one')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    s = Smoke(Path(args.repo) if args.repo else default_repo(), args.since)
    s.check('blame names a law', s.blame)
    s.check('text before and after an amendment', s.on_date)
    s.check('log --follow in date order', s.follow)
    s.check('tags resolve, In-force on every commit, trailers parse', s.tags_and_trailers)
    s.check('only documentation commits are by Lexifina', s.lexifina)
    s.check('README commands run', s.readme)
    s.check('future branch', s.future)
    ok = all(r[1] for r in s.results)
    print(f'{sum(r[1] for r in s.results)}/{len(s.results)} passed')
    if args.record:
        p = HERE / 'verification.json'
        rec = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        rec['smoke'] = {'passed': sum(r[1] for r in s.results), 'total': len(s.results),
                        'results': [{'test': n, 'ok': o, 'detail': d} for n, o, d in s.results]}
        p.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
