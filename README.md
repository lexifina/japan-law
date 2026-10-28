# Japanese law, change by change

Two Japanese laws as a git repository: the Constitution of Japan (日本国憲法) and the Act on the Protection of Personal
Information (個人情報の保護に関する法律, 平成十五年法律第五十七号, the APPI). Each amending law is one commit for each day
it took effect, credited to that law and dated that day (施行日), at noon in Tokyo. The text is the consolidated text
published by the Digital Agency in [e-Gov 法令検索](https://laws.e-gov.go.jp), read through its Law API.

*日本語: [下記](#日本語).*

## The questions, as git commands

| Question | Command |
| --- | --- |
| What did 第二十三条 of the APPI say on 31 March 2022? | `python tools/jiten.py 2022-03-31 kojin-joho 23` |
| And from 1 April 2022, after the 2021 reform renumbered it? | `python tools/jiten.py 2022-04-01 kojin-joho 27` |
| The whole APPI as it stood on 1 January 2020 | `python tools/jiten.py 2020-01-01 kojin-joho` |
| 第九条 of the Constitution | `python tools/jiten.py 2000-01-01 kenpo 9` |
| Which law wrote each line of 第二条 (definitions)? | `git blame kojin-joho/art-002.md` |
| Every change to 第二条, with the law and the day | `git log --follow kojin-joho/art-002.md` |
| Everything one law changed on one day | `git show --stat ac/2021-37/2022-04-01` |
| What changed in the APPI on one day | `git show --stat kojin-joho/2022-04-01` |
| Everything 令和二年法律第四十四号 (the 2020 reform) did, stage by stage | `git log --format="%as %s" --author="Act No. 44 of 2020"` |
| The transitional provisions of the 2015 reform | `python tools/jiten.py 2024-01-01 kojin-joho suppl/h27-65` |
| Laws taking effect in stages (段階施行) | `git log --format="%as %an" --grep="^Stage: "` |
| The baseline: the first text e-Gov holds | `git log --format="%as %an %s" --grep="Kind: baseline"` |
| The amending laws with all their dates | [`laws.csv`](laws.csv) |
| Amendments promulgated but not yet in force | `git log --format="%as %s" main..mishiko` |

## The dates, and which one we use

A Japanese law has the day it was promulgated (公布日, `Promulgated:`) and the day it, or each part of it, took effect
(施行日, `In-force:`). **Commits are dated the day the change took effect**, at noon in Tokyo (UTC+9): that is the day
that decides which text applies. It is the day e-Gov gives for the revision the amendment produced. A law often takes
effect in stages, on several days: each stage is its own commit, with a `Stage:` trailer.

The Constitution took effect on 3 May 1947. Git cannot store dates before 1970, so its commit is dated
1970-01-01; the real day is in `In-force:`, which `tools/jiten.py` reads. Do not query this repository with
`git rev-list --before=`: use `tools/jiten.py`, which picks the version by the `In-force:` trailer.

Amendments already promulgated but not yet in force are on the branch **`mishiko`** (未施行), so `main` is the law in
force on the day the data was retrieved. Some of their days are not yet fixed (政令で定める日): e-Gov records the latest
day the law allows, and those commits say so in a `Date-note:` trailer. After a rebuild, refresh tags with
`git fetch --force --tags`.

## What "author" means

The author of a commit is the law that made the change: `令和三年法律第三十七号 (Act No. 37 of 2021)`, with an address
made of its e-Gov law ID (`503AC0000000037@e-gov.invalid`), which cannot exist, so `git blame` names the law. e-Gov
keeps each law in revisions, and its record of each revision names the one amending law that produced it and the day
that amendment took effect: every change between a revision and the one before is credited to that law. Where two laws
took effect the same day, e-Gov has a revision for each, in the order it applied them, so each has its own commit.

e-Gov's revision history of the APPI begins on 1 March 2017. That first text is the act as amended by every law up to
that day, not the change of one law, so it is committed by the publisher, `e-Gov 法令検索 (デジタル庁)`, labelled
`Kind: baseline`, and credited to no law. Lines that no later law changed still show that author in `git blame`. The
committer is always `Lexifina`.

Blame credits whole lines: a paragraph that two laws amended shows only the later one. Use `git log -p --word-diff`
on the file to see each law's words.

## How it is checked

`tools/check_repo.py` reads every revision of each act back from git on the day it took effect and compares it with
the official text: file by file with the text parsed from e-Gov's XML, and word for word with every text node of the
XML, read independently of the parser. `tools/test_repo.py` checks that the commands above work. The results are in
[`REPRODUCE.md`](REPRODUCE.md).

## Files

Each act is a folder (`kenpo/`, `kojin-joho/`). Each article (条) is one file named after e-Gov's article number:
`kojin-joho/art-016.md` is 第十六条, `kojin-joho/art-016-2.md` is 第十六条の二. The headings of the parts (章, 節, 款)
that begin with an article are `##` lines at the top of its file; the article's caption (見出し) is a line of its own;
each paragraph (項) is one line, the first starting with the article number and each later one with its paragraph
number; each item (号) and sub-item (イ, ロ, …) is a list item. `title.md` is the law number and title, `toc.md` the
table of contents, `preamble.md` the preamble (前文). Each supplementary provision (附則) is one file in `suppl/`:
`original.md` the act's own, and `h27-65.md` the one added by 平成二十七年法律第六十五号 (era letters m, t, s, h, r for
明治, 大正, 昭和, 平成, 令和). Appended tables (別表) are in `appdx/`. A repealed article is removed when e-Gov removes it;
an article e-Gov prints as `削除` stays, with that word.

## What it does not show

- Revisions e-Gov does not hold: the APPI is recorded from 1 March 2017. Its earlier history (2003 to 2017) is not in
  e-Gov's data.
- The amending laws' own words (改め文). The text here is the consolidated text e-Gov made from them.
- How a change applies to earlier facts. The amending laws' transitional provisions (経過措置) are here, in `suppl/`,
  but they are not read as data; read them before relying on a text for a past case.
- Cabinet orders and ministerial ordinances (政令, 府省令) that the APPI delegates to, and the guidelines of the Personal
  Information Protection Commission. Only these two laws are in the record. The same build works for any law in e-Gov:
  add it to `ACTS` in `tools/build.py`.

e-Gov's data is for reference; the authoritative text of a law is the one promulgated in the Official Gazette (官報).

## How it is built

`tools/build.py` reads e-Gov's Law API and writes this repository from scratch; the same data gives the same hashes.
Every step, the software, the decisions made by hand and what an AI model did are in [`REPRODUCE.md`](REPRODUCE.md).
Each act's folder has a `README.md` listing its provisions with how often each changed. [`corpus.json`](corpus.json)
describes the corpus for tools that read several of Lexifina's law repositories.

## Licence

The Constitution and laws are not protected by copyright in Japan (著作権法 第十三条第一号). Source: e-Gov 法令検索
(https://laws.e-gov.go.jp), Digital Agency, used under the Public Data License 1.0 (公共データ利用規約 第1.0版,
https://www.digital.go.jp/resources/open_data/public_data_license_v1.0). The text was split into files and arranged as
a history by Lexifina (加工: Lexifina). The history, commit messages, tables and tools are released under
[CC0 1.0](LICENSE). See [LICENSE](LICENSE).

---

## 日本語

日本国憲法と個人情報の保護に関する法律（平成十五年法律第五十七号）を、改正ごとのgitの履歴にしたもの。本文は
e-Gov 法令検索（デジタル庁）の法令API（Version 2）から取得した。

- **改正法令ごと、施行日ごとに一つのコミット。** 作成者（author）は改正法令（`令和三年法律第三十七号`）なので、
  `git blame` で各行をどの法律が書いたかが分かる。根拠は e-Gov の改正履歴（法令履歴ID）。
- **コミットの日付は施行日**（東京の正午）。公布日もメッセージにある。段階施行は段階ごとに別のコミット。
- **条ごとに一つのファイル、項ごとに一行。** 附則は `suppl/`、別表は `appdx/`。
- **未施行の改正**はブランチ `mishiko` にある。
- **起点:** e-Gov の個人情報保護法の改正履歴は2017年3月1日から。その最初の本文はそれまでの改正をすべて溶け込ませたもの
  なので、法律ではなく e-Gov を作成者とし、`Kind: baseline` と表示している。
- ある日の本文: `python tools/jiten.py 2022-04-01 kojin-joho 27`

出典：e-Gov 法令検索（https://laws.e-gov.go.jp）、PDL1.0。Lexifina が加工して作成。
