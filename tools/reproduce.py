"""Writes data/revisions.json, corpus.json and REPRODUCE.md into the Japanese law repository, from the facts of the
build that made it. Called by build.py; kept apart so the record of how the repository was made reads as one document.

The results of the checks (check_repo.py, test_repo.py and the rebuild that compares hashes) are read from
verification.json next to this file, which check_repo.py, `test_repo.py --record` and `build.py --verify-rebuild` write.
They describe the build before the one that writes this file, from the same data; a rebuild with the same data and the
same verification.json gives the same hashes."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def write_manifest(repo: Path, built: list[dict], today: str):
    """Every source document the text comes from, with its sha256, so a rebuild can show it read the same bytes."""
    out = {'built': today, 'source': 'https://laws.e-gov.go.jp/api/2', 'acts': [{
        'law_id': b['act']['id'], 'law_num': b['num'], 'slug': b['act']['slug'], 'title': b['title'],
        'revisions': [{'law_revision_id': v['id'], 'in_force': v['from'], 'amending_law_id': v['law'],
                       'amending_law_num': v['law_num'], 'promulgated': v['promulgated'], 'status': v['status'],
                       'xml': v['url'], 'sha256': v['sha256']} for v in b['versions']],
    } for b in built]}
    (repo / 'data').mkdir(exist_ok=True)
    (repo / 'data' / 'revisions.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n',
                                                  encoding='utf-8', newline='\n')


def constitution_article(built: list[dict], num: str) -> str:
    """An article of the Constitution as the record holds it, on one line, for corpus.json's authority quote."""
    b = next(b for b in built if b['act']['id'] == '321CONSTITUTION')
    text = b['versions'][0]['units'][f'art-{int(num):03d}']['text']
    return ''.join(l for l in text.split('\n') if l and not l.startswith('#'))


def write_corpus(repo: Path, built: list[dict], today: str):
    first = min(b['versions'][0]['from'] for b in built)
    last = max(v['from'] for b in built for v in b['versions'] if v['from'] <= today)
    corpus = {
        'corpus': 'jp/national/acts',
        'name': 'Japanese law: 日本国憲法 (the Constitution of Japan) and 個人情報の保護に関する法律 '
                '(Act on the Protection of Personal Information, 平成十五年法律第五十七号)',
        'acts': [b['num'] for b in built],
        'history_from': first,
        'built': today,
        'dates': {'commit': 'in-force', 'other_trailers': ['Promulgated'],
                  'time': '12:00 Asia/Tokyo (UTC+9, no summer time)'},
        'scope': {
            'trailer': 'Applies',
            'when_absent': 'this corpus records no scope notes (no commit carries Applies:); the absence is not a '
                           'statement that the change reaches every case',
            'default_reach': {
                'rule': 'no retroactivity unless the law says so (法律不遡及の原則)',
                'meaning': 'an amendment applies from its enforcement day (施行日); how it treats facts and '
                           'proceedings from before that day is set by the transitional provisions (経過措置) in the '
                           'amending law\'s supplementary provisions (附則), which this record includes as '
                           'suppl/<law>.md files but does not read as scope data; the Constitution bars retroactive '
                           'criminal liability, and the general rule outside criminal law is a principle of '
                           'interpretation, not a constitutional rule',
                'authority': '日本国憲法 第三十九条 ("' + constitution_article(built, '39') + '")',
                'decided_here': False,
            },
        },
        'tool': 'tools/jiten.py',
        'in_force_trailer': 'In-force',
        'record_to': last,
        'citation': {
            'file': r'([a-z-]+)/art-0*([0-9]+(?:-[0-9]+)*)\.md',
            'cites': r'第{n}(?![のノ][一二三四五六七八九十])',
            'n_format': 'kanji-article: {n} is the article number in kanji with 条 and any branch numbers, as the '
                        'text writes it: 16 -> 十六条, 16-2 -> 十六条の二, 100 -> 百条, 123 -> 百二十三条',
        },
        'label': 'Japan',
        'language': 'ja',
        'checked_on': today,
        'history': 'in-force',
        'record_note': f'Checked against the official source (e-Gov 法令検索, Law API v2) on {today}. e-Gov keeps '
                       f'revisions of the APPI from {built[1]["versions"][0]["from"]} only; the first is a labelled '
                       'baseline by the publisher, not a law.',
    }
    (repo / 'corpus.json').write_text(json.dumps(corpus, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
                                      newline='\n')


def write_reproduce(repo: Path, built: list[dict], log: list[dict], tags: dict, requests: list[dict], today: str):
    blob = subprocess.run(['git', 'hash-object', str(HERE / 'build.py')], capture_output=True, text=True).stdout.strip()
    pyv = subprocess.run(['python', '--version'], capture_output=True, text=True).stdout.strip()
    gitv = subprocess.run(['git', '--version'], capture_output=True, text=True).stdout.strip()
    try:
        import lxml.etree
        lxmlv = '.'.join(str(x) for x in lxml.etree.LXML_VERSION[:3])
    except Exception:
        lxmlv = '?'
    ver = json.loads((HERE / 'verification.json').read_text(encoding='utf-8')) if (HERE / 'verification.json').exists() else {}
    files = sorted({r['file'] for r in requests if r['file'].exists()})
    days = sorted({dt.date.fromtimestamp(f.stat().st_mtime).isoformat() for f in files})
    data_sha = hashlib.sha256(b''.join(hashlib.sha256(f.read_bytes()).digest() for f in files)).hexdigest()
    urls = {r['url'] for r in requests}
    n_lists = sum(1 for u in urls if '/law_revisions/' in u)
    n_texts = sum(1 for u in urls if '/law_data/' in u)
    n_law = sum(1 for c in log if c['kind'] == 'law' and not c['future'])
    n_future = sum(1 for c in log if c['future'])
    n_empty = sum(1 for c in log if c['kind'] == 'law' and not c['units'])
    n_clamped = sum(1 for c in log if c['clamped'])
    n_changes = sum(len(ch['keys']) for b in built for ch in b['changes'])
    rows = '\n'.join(
        f'| {b["num"]} | {b["title"]} | `{b["act"]["slug"]}/` | {len(b["versions"])} | '
        f'{b["versions"][0]["from"]} to {b["versions"][-1]["from"]} | {len(b["versions"][-1]["units"])} |' for b in built)
    retrieved = ', '.join(days) if days else today
    chk = ver.get('check', {})
    det = ver.get('rebuild', {})
    smoke = ver.get('smoke', {})
    check_line = (f'`{chk["versions"]} revisions checked ({chk["files"]} files), {chk["mismatches"]} mismatches; '
                  f'{chk["wordcheck"]} revisions word for word ({chk["words"]} words) against the whole official text, '
                  f'{chk["word_mismatches"]} mismatches`' if chk else '(not yet run)')
    rebuild_line = (f'A second build from the same cache into an empty folder gave the same history: the last law commit '
                    f'was `{det["history_tip"]}` in both, and every one of the {det["commits"]} law commits and {det["tags"]} '
                    f'tags had the same hash.' if det.get('identical') else '(not yet run)')
    smoke_lines = ('\n'.join(f'   - {"pass" if r["ok"] else "FAIL"}: {r["test"]}: {r["detail"]}' for r in smoke['results'])
                   if smoke else '   (not yet run)')
    smoke_head = f'{smoke["passed"]} of {smoke["total"]} passed' if smoke else 'not yet run'
    staged = sorted({(c['law'], c['author']) for c in log if c['kind'] == 'law'
                     and sum(1 for d in log if d['law'] == c['law']) > 1})
    staged_lines = '\n'.join(f'- {a}: ' + ', '.join(d['day'] for d in log if d['law'] == l) for l, a in staged) or '- none'
    same_day: dict[tuple, list[str]] = {}
    for c in log:
        if c['kind'] == 'law':
            same_day.setdefault((c['slug'], c['day']), []).append(c['author'])
    same_day_lines = '\n'.join(f'- {s} {d}: ' + ', then '.join(a) for (s, d), a in sorted(same_day.items()) if len(a) > 1) or '- none'

    text = f"""# How this history was made, and how to make it again

This file records exactly how the repository was built: the sources, the commands, the software, the decisions made
by hand, and what an AI model did and did not do. The build writes it, so it describes the build that made this
commit.

## Short version

```sh
git clone https://github.com/lexifina/japan-law && cd japan-law
pip install lxml
python -X utf8 tools/build.py --repo ../rebuilt --today {today}
git -C ../rebuilt rev-parse main        # the same hash as this repository's main
python -X utf8 tools/check_repo.py --repo ../rebuilt
python -X utf8 tools/test_repo.py --repo ../rebuilt
```

`tools/build.py` needs Python 3.12 or later with `lxml`, and git. It reads e-Gov's Law API (or its own cache,
`.cache/` next to the script) and writes this repository into `--repo`, which must be empty or a git repository it may
rebuild. With the same e-Gov data and the same `--today` it gives the same commits with the same hashes.
`data/revisions.json` lists every revision it read with the sha256 of the XML, so a rebuild can show it read the same
bytes; e-Gov may change its data (its `updated` field records when), and then the hashes change too. The sha256 over
the sha256s of all {len(files)} cached responses, in file-name order, was `{data_sha}`.

## Sources

All legal text and all information about revisions and amending laws come from **e-Gov 法令検索**
(https://laws.e-gov.go.jp), run by the Digital Agency (デジタル庁), through its **Law API Version 2**. Nothing was typed
in, summarised or rewritten. The build read {n_lists} revision lists and {n_texts} full texts:

| What | Where |
| --- | --- |
| Each law's revisions (改正履歴): the revision ID, the amending law's ID, number and title, its promulgation day (`amendment_promulgate_date`) and the day the amendment took effect (`amendment_enforcement_date`), with e-Gov's status (`CurrentEnforced`, `PreviousEnforced`, `UnEnforced`) | `https://laws.e-gov.go.jp/api/2/law_revisions/<law_id>` (JSON) |
| The full text of each revision, as law XML (法令標準XML) | `https://laws.e-gov.go.jp/api/2/law_data/<law_revision_id>?response_format=xml`, listed with sha256 in `data/revisions.json` |

| Law number | Title | Folder | Revisions | In force from | Files (last revision) |
| --- | --- | --- | ---: | --- | ---: |
{rows}

The data was retrieved on {retrieved}, at most four requests at a time and a request started at most every 0.25
seconds, asking for gzip, with the user agent `lexifina-git-for-law/1.0 (+https://lexifina.com; corpus@lexifina.com)`.
`https://laws.e-gov.go.jp/robots.txt` does not exist (the address answers with the site's single-page application, from
an error at its CDN); `https://www.e-gov.go.jp/robots.txt` has only `User-agent: *` rules for site paths and names no
AI agent. The API needs no key or login. e-Gov's terms (利用規約, https://laws.e-gov.go.jp/terms) apply the Public Data
License 1.0 (公共データ利用規約 第1.0版, PDL1.0), which allows any use, including commercial use, with attribution, and
is compatible with CC BY 4.0; nothing in them limits automated access to the API. e-Gov also offers a bulk download of
current laws (https://laws.e-gov.go.jp/download); it holds no revision history, so the API was used.

## The build, step by step

1. `python -X utf8 scripts/japan-law/build.py --today {today}` in Lexifina's own repository fetched the data into
   its cache and wrote this repository. `tools/build.py` here is the same file as `scripts/japan-law/build.py` there
   (git blob `{blob}`), with `tools/reproduce.py`, which writes this file and `corpus.json`, `tools/check_repo.py` and
   `tools/test_repo.py`. Every later build ran with `--offline`, from the cache.
2. `python -X utf8 scripts/japan-law/check_repo.py` read every revision of each act back from this repository with
   `tools/jiten.py`, on the day it took effect, and compared it file by file with the official text parsed afresh from
   the cached XML; then it compared the whole act, word for word, with every text node of the official XML, read
   without the build's parser. Where two revisions took effect on one day, the earlier is read from its own commit.
   Revisions not yet in force are read from the branch `mishiko`. Result: {check_line}.
3. `python -X utf8 scripts/japan-law/test_repo.py --record` ran the functional smoke test against this repository
   ({smoke_head}):
{smoke_lines}
4. `python -X utf8 scripts/japan-law/build.py --offline --today {today} --verify-rebuild` built the repository a second
   time from the same cache into a temporary folder and compared the hashes. {rebuild_line}
5. The build was run once more to write these results into this file, and the final `main` was rebuilt again in a
   temporary folder and compared hash for hash before it was pushed.
6. `git push -f origin main mishiko --tags` published it to the private GitHub repository `lexifina/japan-law`; once
   that first final build was published, later changes are new commits on top, pushed without `-f`.

It ran with {pyv}, lxml {lxmlv} and {gitv} on Windows 11. No network service other than e-Gov is involved.

## How the text and the commits are derived

Everything below is done by `tools/build.py`, deterministically.

- **Text.** Each act is a folder. Each article (条) of the main provisions is one file named after e-Gov's article
  number: `Num="16"` (第十六条) is `art-016.md`, `Num="16_2"` (第十六条の二) is `art-016-2.md`. The headings of the
  parts (編, 章, 節, 款, 目) that begin with an article are `##` lines at the top of its file. The article's caption
  (見出し, `（目的）`) is a line of its own; then each paragraph (項) is one line, the first beginning with the article's
  title (`第一条　…`) and each later one with its number (`２　…`), separated by a full-width space as e-Gov prints them;
  each item (号) and sub-item (イ, (1), …) is a list item, one level deeper for each level. A sentence block's
  `<Sentence>`s run on as printed; the columns of an item (a term and its definition) are separated by a full-width
  space. Tables are one line per row, `| cell | cell |`. `title.md` holds the law number and title, `toc.md` the table
  of contents (目次), `preamble.md` the preamble (前文); each supplementary provision (附則) is one file,
  `suppl/original.md` for the act's own and `suppl/<era><year>-<number>.md` for one an amending law added
  (`suppl/h27-65.md` is the 附則 of 平成二十七年法律第六十五号; the era letters are m, t, s, h, r for 明治, 大正, 昭和,
  平成, 令和), its first line the label and, in brackets, the amending law's number from e-Gov's `AmendLawNum`; each
  appended table (別表) is `appdx/table-<n>.md`.
- **Normalised.** Nothing inside a line: every character of the XML text is kept, including full-width spaces. Ruby
  readings (`<Rt>`, one in the APPI's history: 禁錮 with こ over 錮) are left out and the base text kept. Whether a
  supplementary provision is printed as an extract (the `Extract` attribute, 抄) is not recorded, because e-Gov sets it
  inconsistently between revisions and it is not text.
- **Changes.** Consecutive revisions are compared file by file. {n_changes} changes of a file were found.
- **Cause.** e-Gov's revision record names the one law whose amendment produced that revision, and the day that
  amendment took effect; the revision ID repeats both (`415AC0000000057_20220401_503AC0000000037`: the APPI as amended
  by 令和三年法律第三十七号 in force on 2022-04-01), and the build checks that they agree. Every difference between a
  revision and the one before is credited to the revision's law. A law amended in stages (段階施行) has one revision,
  and so one commit, per stage, with a `Stage:` trailer. Where two laws took effect the same day, e-Gov has a revision
  for each, in the order it applied them, so each law's change is its own commit; the earlier revision's text is the
  intermediate text, which the check reads at that commit.
- **The baseline.** e-Gov's revision history of the APPI begins on {built[1]["versions"][0]["from"]}. That first
  revision is the whole act as amended to that day; it is committed by the publisher, `e-Gov 法令検索 (デジタル庁)`,
  labelled `Kind: baseline`, and credited to no law, though e-Gov records it as the revision of
  {built[1]["versions"][0]["law_num"]} (whose change of that day cannot be separated from the text before it; its
  later stage is its own commit). The Constitution has one revision, the text as enacted, which is credited to the
  Constitution itself.
- **Date.** The day the amendment took effect (施行日) in e-Gov (`amendment_enforcement_date`), which the revision ID
  repeats. For a revision not yet in force whose day is still to be fixed by cabinet order (政令で定める日), e-Gov gives
  the latest day the law allows as `amendment_scheduled_enforcement_date`; those commits say so in the message and in
  a `Date-note:` trailer.
- **Commits.** One commit per act of the record per revision: {n_law} law commits in force, {n_future} not yet in force
  on the branch `mishiko` (未施行), of which {n_empty} change no words; one for the first revision of each act; then one
  for this documentation.
  - The author is the amending law, `令和三年法律第三十七号 (Act No. 37 of 2021)`, at its e-Gov law ID
    (`503AC0000000037@e-gov.invalid`), an address that cannot exist.
  - Author and committer dates are noon in Tokyo on the day the change took effect, UTC+9 (Japan has had no summer
    time since 1951), written into the code because the build machine has no time-zone database. The committer is
    `Lexifina <japan-law@lexifina.com>`. {n_clamped} commit is before 1970 (the Constitution, in force 1947-05-03); git
    cannot store such dates, so it is dated 1970-01-01T00:00:01Z, with the real day in `In-force:`, which
    `tools/jiten.py` reads.
  - The message has the amending law's title and number, the provisions it inserted, amended or removed (新設, 改正,
    削除), its stages, and the trailers `Promulgated:` (公布日), `In-force:` (施行日), `Enforcement-note:` or
    `Date-note:` (e-Gov's note on the day), `Stage:`, one `Affecting:` line per provision, `Evidence:`, `Revision:` and
    `Previous-revision:` (e-Gov's revision IDs), `Source:` (the law on e-Gov) and `Consolidated:` (the exact API
    address the text came from).
  - Tags: each act's days (`kojin-joho/2022-04-01`, the last commit of that act on that day) and each amending law
    (`ac/2021-37`, the Western year of its number; a law that took effect on several days has one tag per day,
    `ac/2021-37/2022-04-01`); {len(tags)} in all.
- **Documentation commit.** Dated {today}, the day the data was retrieved, not the day of the run, so a later rebuild
  of the same data gives the same hash. It carries `In-force: {today}` and `Kind: documentation`.

Laws that took effect in stages:

{staged_lines}

Laws that took effect on the same day as another, in e-Gov's order:

{same_day_lines}

## Decisions made by hand

These choices were made when the tool was written, after looking at the data. They are in the code.

1. **The acts.** The Constitution of Japan (日本国憲法), never amended: one commit. The Act on the Protection of
   Personal Information (個人情報の保護に関する法律, 平成十五年法律第五十七号), because it is amended often (over twenty
   laws since 2017, including the 2020 and 2021 reforms that rewrote and renumbered it), has staged enforcement, laws
   taking effect on the same day, appended tables, and amendments promulgated but not yet in force.
2. **e-Gov's revision record is the evidence.** The amending laws' own texts (改め文) were not parsed. Each revision
   names one law and one day, so no change in this record needs a `Candidate:` trailer, and none is unexplained.
3. **The baseline is the publisher's.** See above.
4. **Supplementary provisions are text of the act.** e-Gov prints each amending law's 附則 at the end of the act; they
   hold the transitional provisions (経過措置) that decide how a change applies to earlier facts. Each is one file, added
   by the law it belongs to.
5. **Ruby readings and the extract flag are left out** (above).
6. **Japanese only**, the official language. e-Gov's English translations (Japanese Law Translation) are not official
   texts and are not used.

## What an AI model did

This repository was built on {today} in **Claude Code**, Anthropic's coding tool, by the model **Claude Opus 5.5**
(model id `claude-opus-5-5`), working from a brief by the user at Lexifina: a private "git for law" repository for
Japan to the same standard as Lexifina's other corpora.

The model:

- **Researched the source:** e-Gov's Law API v2, its revision records and law XML, its documentation (法令データ
  ドキュメンテーション), its terms (PDL1.0) and robots.txt, and Article 13 of the Copyright Act.
- **Wrote all the code and text in this repository:** `tools/build.py`, `tools/reproduce.py`, `tools/check_repo.py`,
  `tools/test_repo.py`, `tools/jiten.py`, the README, this file and the licence, and chose the design described in
  them.
- **Ran the commands above** and checked the results.

The model did **not**:

- **Write or edit any legal text.** Every word of every provision, every date and every law's number and title is
  copied by the script from e-Gov.
- **Take part in building the history.** No AI model is called when the history is built or checked.

The user decided what was in scope and decides whether the repository is ever made public. The work was not reviewed
line by line by a lawyer. e-Gov's law data is for reference: the authoritative text of a law is the one promulgated in
the Official Gazette (官報).

## Prior art

- [Kohei-Wada/houritsu](https://github.com/Kohei-Wada/houritsu): a volunteer repository of Japanese laws with one
  commit per amendment. Not used; this repository instead dates each change by its 施行日, credits it to the amending
  law, keeps one file per article, and checks every revision against e-Gov.
- [kissge/elaws-history](https://github.com/kissge/elaws-history): a periodic archive of e-Gov's full data dump, dated
  by the day it was taken rather than the day a change took effect. Not used.
- Lexifina's other corpora, whose rules this one follows (Slovakia, Estonia, Liechtenstein, Luxembourg, Monaco, Swiss
  federal law, the Grundgesetz, UK legislation and the US Code).
"""
    (repo / 'REPRODUCE.md').write_text(text, encoding='utf-8', newline='\n')
