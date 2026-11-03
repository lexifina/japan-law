# Japanese law, change by change

8982 Japanese laws and regulations in force as a git repository (4094 Ministerial Ordinances (府省令), 2311 Cabinet Orders (政令), 2101 Acts (法律), 409 Rules (規則), 66 Imperial Ordinances (勅令), 1 the Constitution (憲法)). Each amending law is one commit for each
day it took effect, credited to that law and dated that day (施行日), at noon in Tokyo. The text is the consolidated text
published by the Digital Agency (デジタル庁) in [e-Gov 法令検索](https://laws.e-gov.go.jp): its XML bulk download
(XML一括ダウンロード) for the text in force and not yet in force, and its Law API (Version 2) for each law's list of
revisions and the text of each earlier revision.

**Two kinds of law here.** 607 laws have their revision history: every revision e-Gov holds, one commit per
amending law and day. The other 8375 have, for now, one version only: the text in force on 2026-11-03, dated the day
its latest revision took effect, committed by the publisher and labelled `Label: oldest version available` (and
`Kind: baseline`). Their earlier revisions are added behind them, as new commits on top, without rewriting
anything. [`data/laws.json`](data/laws.json) lists every law with its folder and how many versions it has.

**Earlier versions added later (599 laws so far).** A law first published as its current text gets its earlier
revisions as **correction commits** appended after it, one per version, oldest first (`Kind: correction`). Each says
which days it covers (`Corrects: <folder> <from>..<to>`, to the day before the next version), that it replaces no
published commit (`Supersedes: none`), why (`Reason:`), which folder it is (`Act-path:`) and every file of that version
(`Files:`); its tree holds that version's whole text. A last correction sets the folder back to the text in force now
(`Supersedes:` the current-text commit), so the tip is still today's law. The author of each is the amending law e-Gov
names for that revision (the first is credited as described below). To read a day, take the commit `In-force:` picks
for the folder, then apply each correction whose `Corrects:` range holds that day: `tools/jiten.py` gives the same
result, because it takes the newest commit whose `In-force:` is on or before the day. Because these commits come after
the current text, `git log -- <folder>` on such a law is not in date order and `git blame` at the tip credits the
restoring commit for lines that changed since; read such a law by day with `tools/jiten.py`.
Histories are added in this order: the six codes (六法: 民法, 刑法, 商法, 民事訴訟法, 刑事訴訟法, 会社法), the
most-cited laws, then the rest of the 法律, then 政令, then 府省令.

*日本語: [下記](#日本語).*

## The questions, as git commands

| Question | Command |
| --- | --- |
| What did 第二十三条 of the APPI say on 31 March 2022? | `python tools/jiten.py 2022-03-31 kojin-joho 23` |
| And from 1 April 2022, after the 2021 reform renumbered it? | `python tools/jiten.py 2022-04-01 kojin-joho 27` |
| The whole APPI as it stood on 1 January 2020 | `python tools/jiten.py 2020-01-01 kojin-joho` |
| 第九条 of the Constitution | `python tools/jiten.py 2000-01-01 kenpo 9` |
| 第七百九条 of the Civil Code (民法) today | `python tools/jiten.py 2026-11-03 minpo 709` |
| Every change to the Civil Code's 第五条 (minors), with the law and the day | `git log --format="%as %an" -- minpo/art-005.md` |
| 第百七十六条 of the Penal Code (刑法) on 13 July 2023 | `python tools/jiten.py 2023-07-13 keiho 176` |
| Which law wrote each line of the Companies Act's 第二条 (definitions)? | `git blame kaisha/art-002.md` |
| Which law wrote each line of the APPI's 第二条 (definitions)? | `git blame kojin-joho/art-002.md` |
| Every change to the APPI's 第二条, with the law and the day | `git log --follow kojin-joho/art-002.md` |
| Everything one law changed on one day (first two laws) | `git show --stat ac/2021-37/2022-04-01` |
| What changed in the APPI on one day | `git show --stat kojin-joho/2022-04-01` |
| Everything 令和二年法律第四十四号 (the 2020 reform) did, act by act and stage by stage | `git log --format="%as %s" --author="Act No. 44 of 2020"` |
| The transitional provisions of the 2015 reform | `python tools/jiten.py 2024-01-01 kojin-joho suppl/h27-65` |
| Laws taking effect in stages (段階施行) | `git log --format="%as %an" --grep="^Stage: "` |
| The baselines: the first text e-Gov holds of each law amended before its record begins | `git log --format="%as %an %s" --grep="Kind: baseline"` |
| The laws held as current text only, so far | `git log --format="%as %s" --grep="^Label: oldest version available"` |
| The earlier versions added behind a current text (correction commits) | `git log --format="%as %s" --grep="^Kind: correction"` |
| Which folder is which law | [`data/laws.json`](data/laws.json) |
| The amending laws with all their dates | [`laws.csv`](laws.csv) |
| Amendments promulgated but not yet in force | `git log --format="%as %s" main..mishiko` |

## The dates, and which one we use

A Japanese law has the day it was promulgated (公布日, `Promulgated:`) and the day it, or each part of it, took effect
(施行日, `In-force:`). **Commits are dated the day the change took effect**, at noon in Tokyo (UTC+9): that is the day
that decides which text applies. It is the day e-Gov gives for the revision the amendment produced. A law often takes
effect in stages, on several days: each stage is its own commit, with a `Stage:` trailer.

Git cannot store dates before 1970, so a law whose first text took effect earlier is dated 1970-01-01 (one second
apart, in the order they were added); the real day is in `In-force:`, which `tools/jiten.py` reads.

**Order of the history.** The Constitution and the APPI were built first. Every later law was added on top, as one
block: its first text, then each amendment in the order it took effect. So the history is in date order within each
law's folder, not across the whole repository. Do not query it with `git rev-list --before=` or `git log --until=` over
the whole tree: use `tools/jiten.py`, or `git log -- <folder>`, which pick versions by the `In-force:` trailer and the
folder. Per-file history and `git blame` are exact.

Amendments already promulgated but not yet in force are on the branch **`mishiko`** (未施行), so `main` is the law in
force on the day the data was retrieved. Some of their days are not yet fixed (政令で定める日): e-Gov records the latest
day the law allows, and those commits say so in a `Date-note:` trailer. When such a change comes into force it is added
to `main` as a new commit; the earlier commit stays on `mishiko`.

## What "author" means

The author of a commit is the law that made the change: `令和三年法律第三十七号 (Act No. 37 of 2021)`, with an address
made of its e-Gov law ID (`503AC0000000037@e-gov.invalid`), which cannot exist, so `git blame` names the law. Cabinet
orders and ministerial ordinances that amend are credited the same way (`… (Cabinet Order No. N of YYYY)`,
`… (Ministerial Ordinance No. N of YYYY)`). e-Gov keeps each law in revisions, and its record of each revision names
the one amending law that produced it and the day that amendment took effect: every change between a revision and the
one before is credited to that law. Where two laws took effect the same day, e-Gov has a revision for each, in the
order it applied them, so each has its own commit.

e-Gov's revision history of most laws begins in 2017 or later. The first text it holds of a law amended before then is
the law as amended by every law up to that day, not the change of one law, so it is committed by the publisher,
`e-Gov 法令検索 (デジタル庁)`, labelled `Kind: baseline`, and credited to no law. Lines that no later law changed still show
that author in `git blame`. A law never amended since e-Gov's record begins has its text as enacted, credited to the
law itself. The committer is always `Lexifina`.

Blame credits whole lines: a paragraph that two laws amended shows only the later one. Use `git log -p --word-diff`
on the file to see each law's words.

## How it is checked

Every revision of every law is read back from git on the day it took effect and compared with the official text: file
by file with the text parsed from e-Gov's XML, and word for word with every text node of the XML, read independently of
the parser. `tools/test_repo.py` checks that the commands above work. The results are in [`REPRODUCE.md`](REPRODUCE.md).

## Files

Each law is a folder. The six codes have names: `kenpo/` (日本国憲法), `kojin-joho/` (個人情報の保護に関する法律), `minpo/` (民法), `keiho/` (刑法), `shoho/` (商法), `minji-sosho/` (民事訴訟法), `keiji-sosho/` (刑事訴訟法), `kaisha/` (会社法). Every other law's folder is its e-Gov law ID
(`322AC0000000049/` is 昭和二十二年法律第四十九号); [`data/laws.json`](data/laws.json) gives the title of each. Each
article (条) is one file named after e-Gov's article number: `art-016.md` is 第十六条, `art-016-2.md` is 第十六条の二. The
headings of the parts (編, 章, 節, 款, 目) that begin with an article are `##` lines at the top of its file; the
article's caption (見出し) is a line of its own; each paragraph (項) is one line, the first starting with the article
number and each later one with its paragraph number; each item (号) and sub-item (イ, ロ, …) is a list item. `title.md`
is the law number and title, `toc.md` the table of contents, `preamble.md` the preamble (前文). Each supplementary
provision (附則) is one file in `suppl/`: `original.md` the law's own, and `h27-65.md` the one added by
平成二十七年法律第六十五号 (era letters m, t, s, h, r for 明治, 大正, 昭和, 平成, 令和). Appended tables (別表) are in
`appdx/`. A repealed article is removed when e-Gov removes it; an article e-Gov prints as `削除` stays, with that word.
Each law's folder has a `README.md` listing its provisions with how often each changed. A few laws whose text
the reader cannot split into provisions are one file, `text.md`, with the whole text in order (`Layout: single file`;
0 so far).

## What it does not show

- Revisions e-Gov does not hold: for most laws, anything before 2017.
- Laws not yet added (see `data/laws.json` for those held), and laws no longer in force.
- The amending laws' own words (改め文). The text here is the consolidated text e-Gov made from them.
- How a change applies to earlier facts. The amending laws' transitional provisions (経過措置) are here, in `suppl/`,
  but they are not read as data; read them before relying on a text for a past case.
- Forms, figures and images attached to laws (様式, 別記様式 as images).

e-Gov's data is for reference; the authoritative text of a law is the one promulgated in the Official Gazette (官報).

## Licence

Laws and regulations are not protected by copyright in Japan (著作権法 第十三条第一号). Source: e-Gov 法令検索
(https://laws.e-gov.go.jp), Digital Agency, used under the Public Data License 1.0 (公共データ利用規約 第1.0版,
https://www.digital.go.jp/resources/open_data/public_data_license_v1.0). The text was split into files and arranged as
a history by Lexifina (加工: Lexifina). The history, commit messages, tables and tools are released under
[CC0 1.0](LICENSE). See [LICENSE](LICENSE).

---

## 日本語

e-Gov 法令検索（デジタル庁）が公開する現行の法令を、改正ごとのgitの履歴にしたもの（現在 8982 件。うち改正履歴つき 607 件、
現行の本文のみ 8375 件：「利用可能な最古の版」と表示し、改正履歴は後から上に追加する）。現行・未施行の本文は
XML一括ダウンロード、改正履歴の一覧と過去の改正履歴の本文は法令API（Version 2）から取得した。六法、よく引用される法律、
その他の法律、政令、府省令の順に追加している。

- **改正法令ごと、施行日ごとに一つのコミット。** 作成者（author）は改正法令（`令和三年法律第三十七号`）なので、
  `git blame` で各行をどの法律が書いたかが分かる。根拠は e-Gov の改正履歴（法令履歴ID）。
- **コミットの日付は施行日**（東京の正午）。公布日もメッセージにある。段階施行は段階ごとに別のコミット。
- **法令ごとに一つのフォルダ、条ごとに一つのファイル、項ごとに一行。** 附則は `suppl/`、別表は `appdx/`。フォルダ名は
  六法は名前（`minpo/` など）、その他は法令ID。対応は `data/laws.json`。
- **追加の順序:** 後から追加した法令は、履歴の先端に一つのまとまりとして追加している。ある日の本文は
  `tools/jiten.py` で読む（`In-force:` を見る）。
- **未施行の改正**はブランチ `mishiko` にある。
- **後から追加した過去の版:** 現行の本文だけを先に公開した法令には、その後、過去の改正履歴を訂正（correction）コミットとして
  先端に追加している（`Kind: correction`、`Corrects:` が対象の期間）。ある日の本文は `tools/jiten.py` で読める。
- **起点:** e-Gov の改正履歴は多くの法令で2017年以降。その最初の本文はそれまでの改正をすべて溶け込ませたもの
  なので、法律ではなく e-Gov を作成者とし、`Kind: baseline` と表示している。
- ある日の本文: `python tools/jiten.py 2022-04-01 kojin-joho 27`

出典：e-Gov 法令検索（https://laws.e-gov.go.jp）、PDL1.0。Lexifina が加工して作成。
