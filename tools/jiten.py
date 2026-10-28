"""Prints an act, or one provision of it, as it stood on a given day (時点), from this repository's history.

    python tools/jiten.py 2022-03-31 kojin-joho 23        # 第二十三条 of the APPI on 31 March 2022
    python tools/jiten.py 2022-04-01 kojin-joho 16-2      # 第十六条の二 (also: 16の2)
    python tools/jiten.py 2022-04-01 kojin-joho           # the whole act on 1 April 2022
    python tools/jiten.py 2024-01-01 kojin-joho suppl/r2-44   # the supplementary provisions of 令和二年法律第四十四号
    python tools/jiten.py 2000-01-01 kenpo 9              # 第九条 of the Constitution

Each commit carries the day its change took effect in an `In-force:` trailer (git cannot store dates before 1970, so
the trailer, not the commit date, is the source of truth). The text in force on a day is the last commit on or before
it. Changes promulgated but not yet in force are on the branch "mishiko" (未施行); a date after today reads from there.
Standard library only.
"""
import datetime as dt
import re
import subprocess
import sys

ERA_START = {'m': 1867, 't': 1911, 's': 1925, 'h': 1988, 'r': 2018}


def git(*args: str) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True, encoding='utf-8', check=True).stdout


def order(path: str) -> tuple:
    """The order of the act's files, which is the order of the official text: title, table of contents, preamble,
    articles by number, supplementary provisions by amending law, appended tables."""
    name = path.split('/', 1)[1][:-3]
    if name in ('title', 'toc', 'preamble'):
        return (('title', 'toc', 'preamble').index(name),)
    m = re.fullmatch(r'art-(\d+)((?:-\d+)*)', name)
    if m:
        return (3, int(m.group(1))) + tuple(int(x) for x in m.group(2).split('-')[1:])
    if name == 'suppl/original':
        return (4, 0, 0, 0)
    m = re.fullmatch(r'suppl/([a-z])(\d+)-(\d+)(?:-(\d+))?', name)
    if m:
        return (4, ERA_START[m.group(1)] + int(m.group(2)), int(m.group(3)), int(m.group(4) or 0))
    m = re.fullmatch(r'appdx/table(?:-(\d+))?', name)
    if m:
        return (5, int(m.group(1) or 0))
    return (6, name)


def file_for(key: str) -> str:
    """'16' -> art-016.md; '16-2' or '16の2' -> art-016-2.md; anything else is a file name."""
    m = re.fullmatch(r'(\d+)((?:(?:-|の)\d+)*)', key)
    if m:
        rest = re.findall(r'\d+', m.group(2))
        return '-'.join([f'art-{int(m.group(1)):03d}'] + rest) + '.md'
    return key if key.endswith('.md') else f'{key}.md'


def commit_on(day: str, act: str) -> str:
    future = day > dt.date.today().isoformat() and git('branch', '--list', 'mishiko').strip()
    branch = 'mishiko' if future else 'main'
    # Documentation commits (Kind: documentation) change no law text: they are skipped, so that on the branch
    # mishiko, whose merge of main's documentation is dated the build day, a later day still finds its own law commit.
    out = git('log', '--format=%H%x09%(trailers:key=In-force,valueonly,separator=)%x09'
              '%(trailers:key=Kind,valueonly,separator=)', branch, '--', act)
    for line in out.splitlines():
        h, d, kind = (line.split('\t') + ['', ''])[:3]
        if kind.strip() == 'documentation':
            continue
        if d.strip() and d.strip() <= day:
            return h
    return ''


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    day, act = sys.argv[1], sys.argv[2].strip('/')
    dt.date.fromisoformat(day)
    commit = commit_on(day, act)
    if not commit:
        sys.exit(f'{act} is not in the record on {day}.')
    if len(sys.argv) > 3:
        name = file_for(sys.argv[3])
        try:
            sys.stdout.write(git('show', f'{commit}:{act}/{name}'))
        except subprocess.CalledProcessError:
            sys.exit(f'{act}/{name} was not in the text on {day}.')
        return
    files = [f for f in git('ls-tree', '-r', '--name-only', commit, f'{act}/').split('\n')
             if f.endswith('.md') and not f.endswith('/README.md')]
    files.sort(key=order)
    # Every file in one `git cat-file --batch` (one `git show` per file is slow with hundreds of articles).
    data = subprocess.run(['git', 'cat-file', '--batch'], input=''.join(f'{commit}:{f}\n' for f in files).encode('utf-8'),
                          capture_output=True, check=True).stdout
    pos = 0
    for _ in files:
        nl = data.index(b'\n', pos)
        size = int(data[pos:nl].split()[2])
        sys.stdout.write(data[nl + 1:nl + 1 + size].decode('utf-8') + '\n')
        pos = nl + 1 + size + 1


if __name__ == '__main__':
    main()
