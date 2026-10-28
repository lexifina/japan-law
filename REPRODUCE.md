# How this history was made, and how to make it again

This file records exactly how the repository was built: the sources, the commands, the software, the decisions made
by hand, and what an AI model did and did not do. The build writes it, so it describes the build that made this
commit.

## Short version

```sh
git clone https://github.com/lexifina/japan-law && cd japan-law
pip install lxml
python -X utf8 tools/build.py --repo ../rebuilt --today 2026-10-28
git -C ../rebuilt rev-parse main        # the same hash as this repository's main
python -X utf8 tools/check_repo.py --repo ../rebuilt
python -X utf8 tools/test_repo.py --repo ../rebuilt
```

`tools/build.py` needs Python 3.12 or later with `lxml`, and git. It reads e-Gov's Law API (or its own cache,
`.cache/` next to the script) and writes this repository into `--repo`, which must be empty or a git repository it may
rebuild. With the same e-Gov data and the same `--today` it gives the same commits with the same hashes.
`data/revisions.json` lists every revision it read with the sha256 of the XML, so a rebuild can show it read the same
bytes; e-Gov may change its data (its `updated` field records when), and then the hashes change too. The sha256 over
the sha256s of all 38 cached responses, in file-name order, was `31a5d4cecbd098231b76f9e508341be58dd210ce607f122e4f1c11fcb655cc86`.

## Sources

All legal text and all information about revisions and amending laws come from **e-Gov 法令検索**
(https://laws.e-gov.go.jp), run by the Digital Agency (デジタル庁), through its **Law API Version 2**. Nothing was typed
in, summarised or rewritten. The build read 2 revision lists and 36 full texts:

| What | Where |
| --- | --- |
| Each law's revisions (改正履歴): the revision ID, the amending law's ID, number and title, its promulgation day (`amendment_promulgate_date`) and the day the amendment took effect (`amendment_enforcement_date`), with e-Gov's status (`CurrentEnforced`, `PreviousEnforced`, `UnEnforced`) | `https://laws.e-gov.go.jp/api/2/law_revisions/<law_id>` (JSON) |
| The full text of each revision, as law XML (法令標準XML) | `https://laws.e-gov.go.jp/api/2/law_data/<law_revision_id>?response_format=xml`, listed with sha256 in `data/revisions.json` |

| Law number | Title | Folder | Revisions | In force from | Files (last revision) |
| --- | --- | --- | ---: | --- | ---: |
| 昭和二十一年憲法 | 日本国憲法 | `kenpo/` | 1 | 1947-05-03 to 1947-05-03 | 105 |
| 平成十五年法律第五十七号 | 個人情報の保護に関する法律 | `kojin-joho/` | 35 | 2017-03-01 to 2028-12-23 | 245 |

The data was retrieved on 2026-10-28, at most four requests at a time and a request started at most every 0.25
seconds, asking for gzip, with the user agent `lexifina-git-for-law/1.0 (+https://lexifina.com; corpus@lexifina.com)`.
`https://laws.e-gov.go.jp/robots.txt` does not exist (the address answers with the site's single-page application, from
an error at its CDN); `https://www.e-gov.go.jp/robots.txt` has only `User-agent: *` rules for site paths and names no
AI agent. The API needs no key or login. e-Gov's terms (利用規約, https://laws.e-gov.go.jp/terms) apply the Public Data
License 1.0 (公共データ利用規約 第1.0版, PDL1.0), which allows any use, including commercial use, with attribution, and
is compatible with CC BY 4.0; nothing in them limits automated access to the API. e-Gov also offers a bulk download of
current laws (https://laws.e-gov.go.jp/download); it holds no revision history, so the API was used.

## The build, step by step

1. `python -X utf8 scripts/japan-law/build.py --today 2026-10-28` in Lexifina's own repository fetched the data into
   its cache and wrote this repository. `tools/build.py` here is the same file as `scripts/japan-law/build.py` there
   (git blob `247dd23629eb2c530f06d1a10f1fcd6ee09b83b6`), with `tools/reproduce.py`, which writes this file and `corpus.json`, `tools/check_repo.py` and
   `tools/test_repo.py`. Every later build ran with `--offline`, from the cache.
2. `python -X utf8 scripts/japan-law/check_repo.py` read every revision of each act back from this repository with
   `tools/jiten.py`, on the day it took effect, and compared it file by file with the official text parsed afresh from
   the cached XML; then it compared the whole act, word for word, with every text node of the official XML, read
   without the build's parser. Where two revisions took effect on one day, the earlier is read from its own commit.
   Revisions not yet in force are read from the branch `mishiko`. Result: `36 revisions checked (6315 files), 0 mismatches; 36 revisions word for word (318715 words) against the whole official text, 0 mismatches`.
3. `python -X utf8 scripts/japan-law/test_repo.py --record` ran the functional smoke test against this repository
   (7 of 7 passed):
   - pass: blame names a law: kojin-joho/art-002.md lines by e-Gov 法令検索 (デジタル庁), 令和三年法律第三十七号 (Act No. 37 of 2021), 令和二年法律第四十四号 (Act No. 44 of 2020), 平成二十七年法律第六十五号 (Act No. 65 of 2015)
   - pass: text before and after an amendment: kojin-joho/art-001.md 2022-03-31 != 2022-04-01; kojin-joho/art-132.md 2025-03-31 != 2025-04-01; kenpo 第九条 on 2000-01-01; APPI before 2017-03-01 refused
   - pass: log --follow in date order: kojin-joho/art-002.md 5 commits; kojin-joho/art-027.md 4 commits; kojin-joho/appdx/table-1.md 6 commits
   - pass: tags resolve, In-force on every commit, trailers parse: 66 tags resolve; 37 commits carry In-force; every trailer block parses; no CR in any commit object
   - pass: only the documentation commit is by Lexifina: only the documentation commit 3d04d603dc is by Lexifina; one labelled baseline; 18 authors
   - pass: README commands run: 13 README commands ran and printed output
   - pass: future branch: 6 commits not yet in force, all after 2026-10-28; main has none
4. `python -X utf8 scripts/japan-law/build.py --offline --today 2026-10-28 --verify-rebuild` built the repository a second
   time from the same cache into a temporary folder and compared the hashes. A second build from the same cache into an empty folder gave the same history: the last law commit was `4b47c4e2d2eed2e56057f5feeac05b05eff68652` in both, and every one of the 30 law commits and 66 tags had the same hash.
5. The build was run once more to write these results into this file, and the final `main` was rebuilt again in a
   temporary folder and compared hash for hash before it was pushed.
6. `git push -f origin main mishiko --tags` published it to the private GitHub repository `lexifina/japan-law`; once
   that first final build was published, later changes are new commits on top, pushed without `-f`.

It ran with Python 3.12.10, lxml 6.1.3 and git version 2.46.0.windows.1 on Windows 11. No network service other than e-Gov is involved.

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
- **Changes.** Consecutive revisions are compared file by file. 585 changes of a file were found.
- **Cause.** e-Gov's revision record names the one law whose amendment produced that revision, and the day that
  amendment took effect; the revision ID repeats both (`415AC0000000057_20220401_503AC0000000037`: the APPI as amended
  by 令和三年法律第三十七号 in force on 2022-04-01), and the build checks that they agree. Every difference between a
  revision and the one before is credited to the revision's law. A law amended in stages (段階施行) has one revision,
  and so one commit, per stage, with a `Stage:` trailer. Where two laws took effect the same day, e-Gov has a revision
  for each, in the order it applied them, so each law's change is its own commit; the earlier revision's text is the
  intermediate text, which the check reads at that commit.
- **The baseline.** e-Gov's revision history of the APPI begins on 2017-03-01. That first
  revision is the whole act as amended to that day; it is committed by the publisher, `e-Gov 法令検索 (デジタル庁)`,
  labelled `Kind: baseline`, and credited to no law, though e-Gov records it as the revision of
  平成二十七年法律第六十五号 (whose change of that day cannot be separated from the text before it; its
  later stage is its own commit). The Constitution has one revision, the text as enacted, which is credited to the
  Constitution itself.
- **Date.** The day the amendment took effect (施行日) in e-Gov (`amendment_enforcement_date`), which the revision ID
  repeats. For a revision not yet in force whose day is still to be fixed by cabinet order (政令で定める日), e-Gov gives
  the latest day the law allows as `amendment_scheduled_enforcement_date`; those commits say so in the message and in
  a `Date-note:` trailer.
- **Commits.** One commit per act of the record per revision: 28 law commits in force, 6 not yet in force
  on the branch `mishiko` (未施行), of which 0 change no words; one for the first revision of each act; then one
  for this documentation.
  - The author is the amending law, `令和三年法律第三十七号 (Act No. 37 of 2021)`, at its e-Gov law ID
    (`503AC0000000037@e-gov.invalid`), an address that cannot exist.
  - Author and committer dates are noon in Tokyo on the day the change took effect, UTC+9 (Japan has had no summer
    time since 1951), written into the code because the build machine has no time-zone database. The committer is
    `Lexifina <japan-law@lexifina.com>`. 1 commit is before 1970 (the Constitution, in force 1947-05-03); git
    cannot store such dates, so it is dated 1970-01-01T00:00:01Z, with the real day in `In-force:`, which
    `tools/jiten.py` reads.
  - The message has the amending law's title and number, the provisions it inserted, amended or removed (新設, 改正,
    削除), its stages, and the trailers `Promulgated:` (公布日), `In-force:` (施行日), `Enforcement-note:` or
    `Date-note:` (e-Gov's note on the day), `Stage:`, one `Affecting:` line per provision, `Evidence:`, `Revision:` and
    `Previous-revision:` (e-Gov's revision IDs), `Source:` (the law on e-Gov) and `Consolidated:` (the exact API
    address the text came from).
  - Tags: each act's days (`kojin-joho/2022-04-01`, the last commit of that act on that day) and each amending law
    (`ac/2021-37`, the Western year of its number; a law that took effect on several days has one tag per day,
    `ac/2021-37/2022-04-01`); 66 in all.
- **Documentation commit.** Dated 2026-10-28, the day the data was retrieved, not the day of the run, so a later rebuild
  of the same data gives the same hash. It carries `In-force: 2026-10-28` and `Kind: documentation`.

Laws that took effect in stages:

- 令和二年法律第四十四号 (Act No. 44 of 2020): 2020-06-12, 2020-12-12, 2021-10-01, 2022-04-01
- 令和三年法律第三十七号 (Act No. 37 of 2021): 2021-05-19, 2022-01-01, 2022-04-01, 2022-10-01, 2023-04-01
- 令和四年法律第四十八号 (Act No. 48 of 2022): 2022-05-25, 2026-05-21
- 令和四年法律第六十八号 (Act No. 68 of 2022): 2022-06-17, 2025-06-01
- 令和五年法律第四十七号 (Act No. 47 of 2023): 2023-06-07, 2025-04-01
- 令和五年法律第七十九号 (Act No. 79 of 2023): 2023-11-29, 2024-02-01, 2024-04-01
- 令和八年法律第四十六号 (Act No. 46 of 2026): 2026-06-24, 2028-12-23
- 令和八年法律第五十六号 (Act No. 56 of 2026): 2026-07-17, 2027-01-17, 2028-07-16
- 令和八年法律第六十二号 (Act No. 62 of 2026): 2026-07-17, 2026-11-02

Laws that took effect on the same day as another, in e-Gov's order:

- kojin-joho 2017-05-30: 平成二十七年法律第六十五号 (Act No. 65 of 2015), then 平成二十八年法律第五十一号 (Act No. 51 of 2016)
- kojin-joho 2022-04-01: 令和二年法律第四十四号 (Act No. 44 of 2020), then 令和三年法律第三十七号 (Act No. 37 of 2021)
- kojin-joho 2022-06-17: 令和四年法律第五十四号 (Act No. 54 of 2022), then 令和四年法律第六十八号 (Act No. 68 of 2022)
- kojin-joho 2025-04-01: 令和五年法律第四十七号 (Act No. 47 of 2023), then 令和六年法律第四十六号 (Act No. 46 of 2024)
- kojin-joho 2026-07-17: 令和八年法律第五十六号 (Act No. 56 of 2026), then 令和八年法律第六十二号 (Act No. 62 of 2026)

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

This repository was built on 2026-10-28 in **Claude Code**, Anthropic's coding tool, by the model **Claude Opus 5.5**
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
