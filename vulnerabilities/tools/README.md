# Tools

The scripts behind this Japan-only run of global-law's vulnerability detectors. They run inside a copy of
[global-law/vulnerabilities/scripts](https://github.com/lexifina/global-law/tree/main/vulnerabilities/scripts) (Python 3.11+,
`pip install duckdb pyarrow`), with a bare clone of this repository at `sources/corpus/japan-law.git`, a blobless bare
clone of global-law at `sources/global-law.git`, and a `pins.json` that names only japan-law and its commit.
`build_vulns.py`, `flags_chart.py`, `late_ext_select.py`, `late_ext_rebut.py` and `late_ext_check.py` sit two folders above
the scripts, next to `config.json`.

| Script | What it does |
| --- | --- |
| `run.sh` | Indexes the history and texts, adds this repository's history rows, puts them in date order, and runs the detectors (`bash run.sh <shards>`) |
| `add_root.py` | Builds the history rows from this repository's own commits (global-law replays it only up to an earlier commit), so the history detectors read every change |
| `linearize_jp.py` | Rebuilds the history table in date order and under today's folders (below); `run.sh` stops if it fails |
| `patch_ja.py` | Teaches the detectors Japanese (below; `python -X utf8 patch_ja.py <scripts dir>`, after `patch_detectors.py`; a fix already in place is skipped) |
| `run_triage.sh` | The model review: the 40 strongest flags per category, the 40 strongest lapsed time limits in law texts, and the empty periods |
| `late_ext_select.py` | Chooses the empty periods for global-law's review of that category: those whose old and new date are in one sentence (161 here, so no shortest gaps were added) |
| `late_ext_rebut.py` | Adds the second, arguing-against pass to the empty-period review, as `triage.py` does for the other categories |
| `build_vulns.py` | Builds `data/flags.csv`, `data/reviewed.csv` and `data/by_category.csv` from the findings and the model review |
| `flags_chart.py` | Draws the chart at the top of the READMEs, in Japanese and English, light and dark |
| `config.json` | The repository, the Japanese category names, the top-level folders and files that are not law, and the chart's labels |
| `late_ext_check.py` | Hand-check helper: for each empty period that survived the review, the versions of the provision, and the lines of the extending version's diff that hold the old or the new date, read as the time-limit search reads them |
| `patch_detectors.py` | Fixes blind spots found in runs on several country repositories in the copy of global-law's scripts (`python -X utf8 patch_detectors.py <scripts dir>`; a fix already in place is skipped) |
| `redo.py` | Runs `patch_detectors.py`, then again only the scans and detectors the fixes change, the model review of lapsed time limits, references to deleted provisions and empty periods, and the build (`python -X utf8 redo.py <run folder> [--keep-reviews]`; `EMBED_FONTS` names the script that embeds the chart's fonts). For this repository, run `patch_ja.py` after its patch step; the history table it reads must already be the one `linearize_jp.py` wrote |

The model review needs `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` and `LLM_AUTH` set for an OpenAI-compatible Responses API.
It was run as `bash run_triage.sh '^(data/|tools/|ACTS\.md|REPRODUCE\.md|README)'`.

Changes made for this repository:

- **History in date order (`linearize_jp.py`, run after `add_root.py`).** This repository first published each act as its
  current text (`Kind: baseline`), then appended its earlier versions oldest first as correction commits (`Kind: correction`,
  each holding the act's whole folder as it stood from its `In-force` day), and ended with a correction that sets the
  current text back, credited to e-Gov. Read as git stores it, the first earlier version would be a diff from today's text
  back to the oldest, every change would be of kind `correction` (which the history detectors leave out), and every path
  would be under the act's folder name before 10 November 2026. The script diffs each act's versions in `In-force` order
  instead (the first one counts as the act's first text, every later one as law, credited to the amending law the commit's
  author names), sets the baseline commit aside where a restored current text replaces it, credits the restored current
  text to the law in its `Revision:` trailer (by the name the other versions give that law, or, for an Act or Cabinet
  Order, a name in the same form built from the e-Gov id; otherwise the id), and gives every path under the act's folder
  today (`data/paths.json`). The eight acts kept by short name (`minpo/`, `kaisha/` ...) have ordinary dated law commits,
  which are only moved to their folders today.
- **Japanese (`patch_ja.py`).** Japanese law writes dates in era years and kanji numerals, with "until" after the date, so
  the time-limit search read nothing: it now reads 令和二年三月三十一日まで, …までの間, …限り, 令和五年度（末）まで (31 March
  of the next year) and …月末日まで, with 元年 and numerals written with 十/百/千 or digit by digit; …までに (by) counts as a
  deadline. Amounts in yen written in kanji (五十万円) are read. References: 第十六条の二 is article 16-2 (file
  `art-016-2.md`), not article 16; a reference in a list that begins with another act's name or number
  (公職選挙法施行令第二十二条の二、第二十四条…), in a quotation (「第十七条」とあるのは) or after 附則 is not to the act's own
  article (本法 is the act itself, 基本法 another act); a file such as `art-029-to-031.md` holds articles 29 to 31; a table of
  contents (`toc.md`) cites chapter spans, not provisions; "第十条　削除" (and a range of numbers so marked) is a repeal
  placeholder. The retroactive-date detector also reads the `Promulgated:` trailer as the day a law was made.
- `build_vulns.py` links a provision that is no longer in today's text to the last version of its act that held it, under
  the act's folder at that commit, and matches lapsed-limit reviews on 400 characters of context.
- `flags_chart.py` measures the Japanese legend label at a full em per character, so the two legend entries do not overlap.
- Not changed, and still read wrongly: old acts written with katakana (恩給法) write 第四十九条ノ三 with ノ, which the
  reference search reads as article 49; references after a parenthesis of more than 80 characters, or after a list longer
  than the search looks back, are taken as the act's own; a range file with three-level numbers
  (`art-007-2-3-to-007-2-8.md`) is not read as a range.
