"""Functional smoke test of the built Japanese law repository: the things a reader does with it work. Standard library
only.

    python -X utf8 scripts/japan-law/test_repo.py [--repo ../japan-law] [--record]
    python -X utf8 tools/test_repo.py                   # from inside the repository

It asserts that:
1. `git blame` on a changed provision names amending laws as authors of its lines;
2. tools/jiten.py gives the text before and after a known amendment, and each equals the file at that day's tag;
3. `git log --follow` on a file lists its amending laws in the order they took effect;
4. every tag resolves to a commit, and every commit has an `In-force:` trailer, and every trailer block parses;
5. no commit is authored by Lexifina except the documentation commit (the last one), and only the labelled baseline
   is by the publisher;
6. every git or tool command in the README's table runs and prints something;
7. the branch mishiko holds only changes not yet in force, on top of main.
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
LAW = re.compile(r'^(明治|大正|昭和|平成|令和)\S+年法律第\S+号 \(Act No\. \d+ of \d{4}\)$|^日本国憲法 \(The Constitution of Japan\)$')
PUBLISHER = 'e-Gov 法令検索 (デジタル庁)'


def default_repo() -> Path:
    if (HERE.parent / '.git').exists():
        return HERE.parent
    return HERE.parents[2] / 'japan-law'


class Smoke:
    def __init__(self, repo: Path):
        self.repo = repo
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
        bad = [r for r in rows if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', r.split('\t')[2].strip())]
        assert not bad, f'{len(bad)} commits without a well-formed In-force, e.g. {bad[:2]}'
        unparsed = []
        for h in [r.split('\t')[0] for r in rows]:
            body = self.git('log', '-1', '--format=%B', h)
            last = body.rstrip('\n').split('\n\n')[-1]
            parsed = subprocess.run(['git', 'interpret-trailers', '--parse'], cwd=self.repo, input=body,
                                    capture_output=True, text=True, encoding='utf-8').stdout
            if parsed.strip() != last.strip():
                unparsed.append(h[:10])
        assert not unparsed, f'trailer blocks git does not parse: {unparsed[:3]}'
        objs = subprocess.run(['git', 'cat-file', '--batch'], cwd=self.repo, capture_output=True,
                              input=''.join(r.split('\t')[0] + '\n' for r in rows).encode()).stdout
        assert b'\r' not in objs, 'a commit object holds a carriage return (CRLF message)'
        return f'{len(tags)} tags resolve; {len(rows)} commits carry In-force; every trailer block parses; no CR in any commit object'

    # 5
    def lexifina(self):
        rows = self.git('log', '--format=%H%x09%an%x09%ae%x09%cn%x09%B%x1e', 'main').split('\x1e')
        rows = [r.strip('\n').split('\t', 4) for r in rows if r.strip()]
        by_lex = [r for r in rows if r[1] == 'Lexifina']
        assert len(by_lex) == 1 and by_lex[0] == rows[0], f'{len(by_lex)} commits by Lexifina'
        assert all(r[3] == 'Lexifina' for r in rows), 'a committer other than Lexifina'
        pub = [r for r in rows if r[1] == PUBLISHER]
        assert len(pub) == 1 and 'Kind: baseline' in pub[0][4], f'{len(pub)} publisher commits, or one not labelled'
        authors = {r[1] for r in rows[1:]}
        assert all(LAW.match(a) or a == PUBLISHER for a in authors), f'unexpected authors {authors - {PUBLISHER}}'
        assert all(r[2].endswith('.invalid') for r in rows[1:]), 'an author address that is not .invalid'
        return f'only the documentation commit {rows[0][0][:10]} is by Lexifina; one labelled baseline; {len(authors)} authors'

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
        rows = self.git('log', '--no-merges', '--format=%(trailers:key=In-force,valueonly,separator=)',
                        'main..mishiko').split()
        assert rows and all(d > built for d in rows), f'mishiko holds changes in force by {built}: {rows}'
        main_days = self.git('log', '--format=%(trailers:key=In-force,valueonly,separator=)', 'main').split()
        assert all(d <= built for d in main_days), 'main holds a change not yet in force'
        return f'{len(rows)} commits not yet in force, all after {built}; main has none'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=None)
    ap.add_argument('--record', action='store_true')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    s = Smoke(Path(args.repo) if args.repo else default_repo())
    s.check('blame names a law', s.blame)
    s.check('text before and after an amendment', s.on_date)
    s.check('log --follow in date order', s.follow)
    s.check('tags resolve, In-force on every commit, trailers parse', s.tags_and_trailers)
    s.check('only the documentation commit is by Lexifina', s.lexifina)
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
