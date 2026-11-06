# How this history was made

This file records how the repository was made: the sources, the steps, the checks, the decisions made by hand, and
what an AI model did and did not do. It is rewritten by each documentation commit, so it describes the history up to
that commit; earlier versions are in the history of this file.

## Sources

All legal text and all information about revisions and amending laws come from **e-Gov 法令検索**
(https://laws.e-gov.go.jp), run by the Digital Agency (デジタル庁). Nothing was typed in, summarised or rewritten.

| What | Where |
| --- | --- |
| The text in force, and the text of each revision promulgated but not yet in force, of every law in e-Gov, as law XML (法令標準XML), with e-Gov's list of them (`all_law_list.csv`) | e-Gov's XML bulk download (XML一括ダウンロード), all laws: `https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true` (data of 2026-11-02, sha256 `8047be32c9424a4aba2029b0c5dff5bafbb292ed95a0dd11adf46125e05e8755`) |
| Each law's revisions (改正履歴): the revision ID, the amending law's ID, number and title, its promulgation day and the day the amendment took effect, with e-Gov's status (`CurrentEnforced`, `PreviousEnforced`, `UnEnforced`) | Law API Version 2: `https://laws.e-gov.go.jp/api/2/law_revisions/<law_id>` |
| The full text of each earlier revision, as law XML | Law API Version 2: `https://laws.e-gov.go.jp/api/2/law_data/<law_revision_id>?response_format=xml` |

The bulk download and the Law API serve the same XML: for every revision both hold that was compared, the `<Law>`
element was identical after XML canonicalisation. `data/revisions.json` lists every revision used, the address of its
text in the Law API, which of the two sources the text was taken from (`text_from`) and the sha256 of that XML.

e-Gov's terms of use (利用規約, https://laws.e-gov.go.jp/terms) apply the Public Data License 1.0 (公共データ利用規約
第1.0版, PDL1.0), which allows any use, including commercial use, with attribution and a note of any processing, and is
compatible with CC BY 4.0. See [LICENSE](LICENSE).

## What is in it

8982 laws (4094 Ministerial Ordinances (府省令), 2311 Cabinet Orders (政令), 2101 Acts (法律), 409 Rules (規則), 66 Imperial Ordinances (勅令), 1 the Constitution (憲法)): 43828 revisions in force and
1138 not yet in force (on `mishiko`); 8601 laws begin with a labelled
baseline; 5583 amending laws take effect in stages in at least one of them. [`data/laws.json`](data/laws.json)
lists each law with its folder, and [`laws.csv`](laws.csv) each amending law with its dates.

## How the history was made

1. **First build (2026-10-28).** The Constitution and the APPI, built from scratch; see the earlier versions of this
   file (`git log -- REPRODUCE.md`).
2. **Appends.** Since then the history only grows: nothing published is rewritten, no tag is moved. Each append adds,
   on top of `main`:
   - each new law as one block: its first revision in e-Gov (labelled `Kind: baseline` if e-Gov records it as made by
     an amending law, as above), then one commit per later revision in force, in e-Gov's order;
   - for a law already held, the revisions that have come into force since, as changes from the newest one held, after
     checking that the one held still reads back exactly as e-Gov has it (a difference would be a correction, made
     only in a labelled commit decided by hand);
   - for a law first published as its current text alone, its earlier revisions, as labelled correction commits after
     it (see the README): one per version in force at the end of its day, oldest first, each holding that version's
     whole text and naming its days (`Corrects:`), then one that sets the folder back to the text in force now. The
     current text published before must first read back exactly as e-Gov's current revision; a law where it does not
     is held. A revision e-Gov replaced on its own day was never in force at the end of a day and gets no commit;
   - a documentation commit (this file, the tables, `data/`).
   Then `mishiko` gets a merge of the new `main` (the folders of laws that already have changes on `mishiko` keep its
   text, which already holds every change `main` has since received), and each new law's revisions not yet in force.
   - Author dates are the in-force day, noon in Tokyo. Committer dates are the previous head's plus one second per
     commit, so they never go backwards and the same data on the same head gives the same hashes.
   - Tags: `<folder>/<day>` for each law and day. The amending-law tags of the first build (`ac/2021-37`, …) are kept;
     they are not made for laws added later, because a law that amends several acts added in separate blocks has no
     single commit with all its changes. Use `git log --author="Act No. 37 of 2021"` instead.

| Day | Onto | Commits | New laws | Laws extended | Not yet in force |
| --- | --- | ---: | ---: | --- | ---: |
| 2026-11-02 | `9d587c504273` | 130 | 6 | kojin-joho | 16 |
| 2026-11-03 | `959dcff3d6bd` | 500 | 500 | - | 0 |
| 2026-11-03 | `c6522fbb8abc` | 500 | 500 | - | 0 |
| 2026-11-03 | `a8315924f803` | 500 | 500 | - | 0 |
| 2026-11-03 | `87d60a193fe2` | 500 | 500 | - | 0 |
| 2026-11-03 | `c077311d8bca` | 500 | 500 | - | 0 |
| 2026-11-03 | `fe6dfc72b496` | 500 | 500 | - | 0 |
| 2026-11-03 | `b70e780587a6` | 500 | 500 | - | 0 |
| 2026-11-03 | `6f0d502da15b` | 500 | 500 | - | 0 |
| 2026-11-03 | `7d2fe1a87bb6` | 500 | 500 | - | 0 |
| 2026-11-03 | `449ae959f821` | 500 | 500 | - | 0 |
| 2026-11-03 | `6e087e54b093` | 500 | 500 | - | 0 |
| 2026-11-03 | `81b2d868fbab` | 500 | 500 | - | 0 |
| 2026-11-03 | `f5a963b0a6ac` | 500 | 500 | - | 0 |
| 2026-11-03 | `ff68ac047371` | 500 | 500 | - | 0 |
| 2026-11-03 | `f9792f8f7d09` | 500 | 500 | - | 0 |
| 2026-11-03 | `45c7156e1824` | 500 | 500 | - | 0 |
| 2026-11-03 | `68af551f1603` | 500 | 500 | - | 0 |
| 2026-11-03 | `acb8292f7fd2` | 474 | 474 | - | 0 |
| 2026-11-03 | `a9244402cd5d` | 3357 | 0 | 299 laws given their earlier versions (3357 correction commits) | 231 |
| 2026-11-03 | `2a41972f04c3` | 2675 | 0 | 299 laws given their earlier versions (2675 correction commits) | 194 |
| 2026-11-03 | `43b5135ae5b2` | 2352 | 0 | 300 laws given their earlier versions (2352 correction commits) | 128 |
| 2026-11-03 | `8b1cc92fbc69` | 2361 | 0 | 298 laws given their earlier versions (2361 correction commits) | 161 |
| 2026-11-05 | `c6bac009c3ae` | 2274 | 0 | 300 laws given their earlier versions (2274 correction commits) | 87 |
| 2026-11-05 | `4c3a56e73aa1` | 2226 | 0 | 300 laws given their earlier versions (2226 correction commits) | 46 |
| 2026-11-05 | `b70e090ee225` | 1989 | 0 | 299 laws given their earlier versions (1989 correction commits) | 28 |
| 2026-11-05 | `7e7a10fb72fb` | 2122 | 0 | 300 laws given their earlier versions (2122 correction commits) | 26 |
| 2026-11-05 | `509b479bcb6f` | 2272 | 0 | 299 laws given their earlier versions (2272 correction commits) | 37 |
| 2026-11-05 | `bbb4b5b66782` | 2777 | 0 | 300 laws given their earlier versions (2777 correction commits) | 56 |
| 2026-11-06 | `0f7036149ad2` | 2483 | 0 | 299 laws given their earlier versions (2483 correction commits) | 52 |
| 2026-11-06 | `d1a94add3df1` | 2522 | 0 | 298 laws given their earlier versions (2522 correction commits) | 41 |
| 2026-11-06 | `6f204be92d47` | 2204 | 0 | 300 laws given their earlier versions (2204 correction commits) | 13 |
| 2026-11-06 | `06f271c2d072` | 4017 | 0 | 599 laws given their earlier versions (4017 correction commits) | 28 |

The text of each revision is turned into files exactly as in the first build: one file per article, `suppl/` for the
supplementary provisions, `appdx/` for the appended tables, ruby readings left out, nothing else changed in a line.
Each commit's message has the amending law's title and number, the provisions it inserted, amended or removed (新設,
改正, 削除), its stages, and the trailers `Promulgated:`, `In-force:`, `Enforcement-note:` or `Date-note:`, `Stage:`,
`Affecting:`, `Evidence:`, `Revision:` and `Previous-revision:` (e-Gov's revision IDs), `Source:` and `Consolidated:`.

## Checks of the latest append

1. **Against the official text.** Every revision of every law the append added, and the revisions now in force of the
   laws it extended, read back from git on the day they took effect (the way `tools/jiten.py` reads them), compared
   file by file with the text parsed from e-Gov's XML, and word for word with every text node of the XML read without
   the parser. Revisions not yet in force are read from `mishiko`. Result: 4082 revisions of 602 laws checked (450825 files), 0 mismatches; 4082 revisions word for word (23297082 words), 0 mismatches; 0 history problems.
2. **Published history unchanged.** The previous `main` and `mishiko` are ancestors of the new ones; every tag that
   existed points where it did; the folders of laws not extended are unchanged.
3. **`tools/test_repo.py`** (7 of 7 passed):
   - pass: blame names a law: kojin-joho/art-002.md lines by e-Gov 法令検索 (デジタル庁), 令和三年法律第三十七号 (Act No. 37 of 2021), 令和二年法律第四十四号 (Act No. 44 of 2020), 令和八年法律第六十二号 (Act No. 62 of 2026), 平成二十七年法律第六十五号 (Act No. 65 of 2015)
   - pass: text before and after an amendment: kojin-joho/art-001.md 2022-03-31 != 2022-04-01; kojin-joho/art-132.md 2025-03-31 != 2025-04-01; kenpo 第九条 on 2000-01-01; APPI before 2017-03-01 refused
   - pass: log --follow in date order: kojin-joho/art-002.md 6 commits; kojin-joho/art-027.md 4 commits; kojin-joho/appdx/table-1.md 6 commits
   - pass: tags resolve, In-force on every commit, trailers parse: 10233 tags resolve; 45949 commits carry In-force; the trailer blocks of 5168 commits parse; no CR in any commit object
   - pass: only documentation commits are by Lexifina: 34 documentation commits by Lexifina, the last one on top; 17585 labelled baselines; 9547 authors
   - pass: README commands run: 19 README commands ran and printed output
   - pass: future branch: 1149 commits not yet in force, all after 2026-11-06; 1 since in force, and on main too; main has none after that day

Software: Python 3.14.4, lxml 6.1.3, git version 2.53.0.

## Decisions made by hand

1. **Scope and order.** Every law in e-Gov's bulk download, in force or promulgated: the six codes first, then a
   hand-picked list of the most-cited laws, then the rest by type (法律, 政令, 勅令, 府省令, 規則), each by law ID.
2. **e-Gov's revision record is the evidence.** The amending laws' own texts (改め文) were not parsed. Each revision
   names one law and one day.
3. **The baseline is the publisher's.** See the README.
4. **Supplementary provisions are text of the law.** Each is one file, added by the law it belongs to.
5. **Ruby readings and the extract flag are left out**, as in the first build.
6. **Earlier versions as corrections.** The published history only grows, so the earlier revisions of a law published
   first as its current text cannot go before it: they are appended after it as correction commits in the shared
   git-for-law format (`Kind: correction`, `In-force:`, `Corrects:`, `Supersedes:`, `Reason:`, `Act-path:`, `Files:`),
   which readers apply by day. No tag is added for a correction.
7. **Breadth first.** Every law not yet given its history is published as its current text alone, one version labelled
   `oldest version available`, so the whole statute book is here before the histories are; the histories follow as
   new commits on top. A current text the reader cannot split into provisions is published as a single-file act
   (`text.md`, `Layout: single file`), its words still checked against the XML. A law whose history the parser
   cannot read exactly is held, not approximated, and listed for later work.
8. **Japanese only**, the official language.

## What an AI model did

The history was built in **Claude Code**, Anthropic's coding tool, by the model **Claude Opus 5.5** (model id
`claude-opus-5-5`), working from a brief by the user at Lexifina. The model wrote the code that turns e-Gov's data into
this history and these documents, ran it, and checked the results. It did **not** write or edit any legal text: every
word of every provision, every date and every law's number and title is copied by the code from e-Gov. No AI model is
called when the history is built or checked. The work was not reviewed line by line by a lawyer. e-Gov's law data is
for reference: the authoritative text of a law is the one promulgated in the Official Gazette (官報).
